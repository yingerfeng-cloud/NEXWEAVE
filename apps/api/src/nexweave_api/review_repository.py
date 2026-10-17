"""M6 PostgreSQL service for governed Claims, Conflicts and HumanReview."""
# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.derived_reads import DerivedReadGate
from nexweave_api.errors import ApiProblem
from nexweave_api.knowledge_repository import KnowledgeRepository
from nexweave_api.repository import JsonDict, _json_value
from nexweave_api.review_content import (
    TABLES,
    checked_revision,
    content,
    load_target,
    modify_target,
    record_revision,
)
from nexweave_domain import (
    ConflictResolution,
    Principal,
    ReviewDecision,
    ReviewPolicy,
    ReviewRuleViolation,
    ReviewStage,
    RiskLevel,
    new_uuid7,
    validate_evidence_gate,
    validate_final_approval_separation,
    validate_review_policy,
)
from nexweave_domain.review import validate_stage_role


class ReviewRepository(KnowledgeRepository):
    async def _review_context(
        self,
        connection: AsyncConnection,
        principal: Principal,
        space_id: UUID,
        kind: str,
        object_id: UUID,
    ) -> JsonDict:
        await DerivedReadGate(connection, principal, space_id, self.record_denial).require(
            kind, object_id
        )
        table = {**TABLES, "CLAIM": "claims", "RELATION": "relations"}.get(kind)
        if table is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Context unavailable", "Context unavailable."
            )
        row = (
            (
                await connection.execute(
                    text(
                        f"SELECT * FROM {table} WHERE id=:id AND tenant_id=:tenant AND space_id=:space"  # noqa: S608
                    ),
                    {"id": object_id, "tenant": principal.tenant_id, "space": space_id},
                )
            )
            .mappings()
            .one()
        )
        column = {
            "CLAIM_CANDIDATE": "claim_candidate_id",
            "RELATION_CANDIDATE": "relation_candidate_id",
            "CLAIM": "claim_id",
            "RELATION": "relation_id",
        }.get(kind)
        evidence_table = (
            "evidence_records" if kind in {"CLAIM", "RELATION"} else "evidence_candidates"
        )
        evidence = []
        if column:
            evidence = list(
                (
                    await connection.execute(
                        text(
                            f"SELECT ec.*,sa.source_version_id,sa.status AS anchor_status,sa.locators,sv.filename "  # noqa: S608
                            f"FROM {evidence_table} ec JOIN source_anchors sa ON sa.id=ec.source_anchor_id "
                            f"JOIN source_versions sv ON sv.id=sa.source_version_id WHERE ec.{column}=:id ORDER BY ec.created_at"
                        ),
                        {"id": object_id},
                    )
                )
                .mappings()
                .all()
            )
        if kind == "WIKI_PAGE_VERSION":
            # The immutable page may include earlier generated/protected sections.
            # Show every earlier page compilation anchor rather than inventing a
            # supporting Claim or silently omitting inherited source dependencies.
            evidence = list(
                (
                    await connection.execute(
                        text(
                            "SELECT DISTINCT sa.id,sa.id AS source_anchor_id,sa.source_version_id,"
                            "sa.status AS anchor_status,sa.locators,sa.excerpt_hash,sv.filename,"
                            "'CONTEXT' AS stance FROM wiki_page_versions pv "
                            "JOIN compile_job_sources cs ON cs.compile_job_id=pv.compile_job_id "
                            "JOIN source_anchors sa ON sa.source_version_id=cs.source_version_id "
                            "JOIN source_versions sv ON sv.id=sa.source_version_id "
                            "WHERE pv.wiki_page_id=:page AND pv.revision<=:revision "
                            "AND sa.parse_job_id=sv.active_parse_job_id"
                        ),
                        {"page": row["wiki_page_id"], "revision": row["revision"]},
                    )
                )
                .mappings()
                .all()
            )
        entity_labels: dict[str, str] = {}
        if kind in {"RELATION_CANDIDATE", "RELATION"}:
            for entity_id in (row["source_entity_id"], row["target_entity_id"]):
                if not await DerivedReadGate(connection, principal, space_id).can_read(
                    "ENTITY", entity_id
                ):
                    continue
                label = (
                    await connection.execute(
                        text(
                            "SELECT display_name FROM knowledge_entities WHERE id=:id "
                            "AND tenant_id=:tenant AND space_id=:space"
                        ),
                        {"id": entity_id, "tenant": principal.tenant_id, "space": space_id},
                    )
                ).scalar_one_or_none()
                if label is not None:
                    entity_labels[str(entity_id)] = str(label)
        opened = (
            await connection.execute(
                text(
                    "SELECT id FROM review_cases WHERE tenant_id=:tenant AND space_id=:space "
                    "AND target_type=:kind AND target_id=:id AND status IN ('OPEN','WAITING_EVIDENCE','OVERDUE') ORDER BY created_at DESC LIMIT 1"
                ),
                {"tenant": principal.tenant_id, "space": space_id, "kind": kind, "id": object_id},
            )
        ).scalar_one_or_none()
        return _json_value(
            {
                "id": object_id,
                "target_type": kind,
                "content": content(row),
                "entity_labels": entity_labels,
                "evidence": [dict(item) for item in evidence],
                "open_review_case_id": opened,
            }
        )

    async def list_review_targets(
        self, *, principal: Principal, space_id: UUID, limit: int = 100
    ) -> JsonDict:
        principal = await self.principal_for_space(
            principal=principal, space_id=space_id, action="review.read"
        )
        values = []
        async with self._database.engine.connect() as connection:
            gate = DerivedReadGate(connection, principal, space_id)
            for kind, table in TABLES.items():
                rows = (
                    (
                        await connection.execute(
                            text(
                                f"SELECT t.id,t.created_at FROM {table} t WHERE tenant_id=:tenant AND space_id=:space "  # noqa: S608
                                "AND (:kind!='WIKI_PAGE_VERSION' OR t.status!='APPROVED') "
                                "AND NOT EXISTS (SELECT 1 FROM review_cases rc WHERE rc.target_type=:kind AND rc.target_id=t.id AND rc.status='APPROVED') "
                                "ORDER BY t.created_at DESC,t.id DESC LIMIT :limit"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "kind": kind,
                                "limit": limit + 1,
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                for row in rows:
                    if await gate.can_read(kind, row["id"]):
                        values.append((row["created_at"], kind, row["id"]))
            values.sort(key=lambda r: (r[0], str(r[2])), reverse=True)
            return {
                "items": [
                    await self._review_context(connection, principal, space_id, kind, object_id)
                    for _, kind, object_id in values[:limit]
                ],
                "truncated": len(values) > limit,
            }

    async def list_relations(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        principal = await self.principal_for_space(
            principal=principal, space_id=space_id, action="claim.read"
        )
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM relations WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
            gate = DerivedReadGate(connection, principal, space_id)
            return [_json_value(row) for row in rows if await gate.can_read("RELATION", row["id"])]

    async def create_review_policy(
        self, *, principal: Principal, space_id: UUID, payload: dict[str, Any], trace_id: str
    ) -> JsonDict:
        try:
            policy = ReviewPolicy(
                RiskLevel(payload["risk_level"]),
                tuple(ReviewStage(value) for value in payload["stages"]),
                bool(payload["allow_batch"]),
                int(payload["batch_limit"]),
            )
            validate_review_policy(policy)
        except (ValueError, ReviewRuleViolation) as exc:
            raise ApiProblem(
                422,
                getattr(exc, "code", "REVIEW_POLICY_INVALID"),
                "Review policy rejected",
                str(exc),
            ) from exc
        now, policy_id = datetime.now(UTC), new_uuid7()
        async with self._database.engine.begin() as connection:
            version = int(
                (
                    await connection.execute(
                        text(
                            "SELECT COALESCE(MAX(version),0)+1 FROM review_policies WHERE space_id=:space AND risk_level=:risk"
                        ),
                        {"space": space_id, "risk": policy.risk.value},
                    )
                ).scalar_one()
            )
            await connection.execute(
                text(
                    "INSERT INTO review_policies (id,tenant_id,space_id,risk_level,stages,timeout_seconds,escalation_role,allow_batch,batch_limit,source_authority_rules,status,version,created_at,created_by) VALUES (:id,:tenant,:space,:risk,CAST(:stages AS jsonb),:timeout,:role,:batch,:limit,CAST(:rules AS jsonb),'ACTIVE',:version,:now,:actor)"
                ),
                {
                    "id": policy_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "risk": policy.risk.value,
                    "stages": json.dumps([stage.value for stage in policy.stages]),
                    "timeout": payload["timeout_seconds"],
                    "role": payload["escalation_role"],
                    "batch": policy.allow_batch,
                    "limit": policy.batch_limit,
                    "rules": json.dumps(payload.get("source_authority_rules", {})),
                    "version": version,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="review.policy.create",
                resource_type="ReviewPolicy",
                resource_id=policy_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"risk": policy.risk.value, "version": version},
            )
        return await self.get_review_policy(principal=principal, policy_id=policy_id)

    async def get_review_policy(self, *, principal: Principal, policy_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM review_policies WHERE tenant_id=:tenant AND id=:id"),
                        {"tenant": principal.tenant_id, "id": policy_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Review policy unavailable",
                "The review policy is unavailable.",
            )
        return _json_value(row)

    async def list_review_policies(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM review_policies WHERE tenant_id=:tenant AND space_id=:space AND status='ACTIVE' ORDER BY risk_level,version DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def list_claims(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        principal = await self.principal_for_space(
            principal=principal, space_id=space_id, action="claim.read"
        )
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT c.*,cc.schema_version_id FROM claims c JOIN claim_candidates cc ON cc.id=c.candidate_id WHERE c.tenant_id=:tenant AND c.space_id=:space ORDER BY c.created_at DESC,c.id DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
            gate = DerivedReadGate(connection, principal, space_id, self.record_denial)
            return [_json_value(row) for row in rows if await gate.can_read("CLAIM", row["id"])]

    async def list_evidence(self, *, principal: Principal, claim_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT er.* FROM evidence_records er JOIN claims c ON c.id=er.claim_id WHERE c.tenant_id=:tenant AND er.claim_id=:claim ORDER BY er.created_at"
                        ),
                        {"tenant": principal.tenant_id, "claim": claim_id},
                    )
                )
                .mappings()
                .all()
            )
            if not rows:
                return []
            space_id = UUID(str(rows[0]["space_id"]))
            principal = await self.principal_for_space(
                principal=principal, space_id=space_id, action="claim.read"
            )
            gate = DerivedReadGate(connection, principal, space_id, self.record_denial)
            await gate.require("CLAIM", claim_id)
            return [_json_value(row) for row in rows if await gate.can_read("EVIDENCE", row["id"])]

    async def create_review_case(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        workflow_task_id: UUID,
        trace_id: str,
    ) -> JsonDict:
        principal = await self.principal_for_space(
            principal=principal, space_id=space_id, action="review.create"
        )
        policy = await self.get_review_policy(
            principal=principal, policy_id=UUID(str(payload["policy_id"]))
        )
        if policy["space_id"] != str(space_id) or policy["risk_level"] != payload["risk_level"]:
            raise ApiProblem(
                409,
                "REVIEW_POLICY_SCOPE_CONFLICT",
                "Review policy conflict",
                "Policy does not match this space and risk level.",
            )
        async with self._database.engine.connect() as connection:
            existing = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,target_id,target_type,policy_id,risk_level,reason FROM review_cases WHERE workflow_task_id=:id AND tenant_id=:tenant"
                        ),
                        {"id": workflow_task_id, "tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .first()
            )
        if existing is not None:
            if any(
                str(existing[k]) != str(payload[k])
                for k in ("target_id", "target_type", "policy_id", "risk_level", "reason")
            ):
                raise ApiProblem(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Review inputs changed",
                    "Use a fresh request ID.",
                )
            return await self.get_review_case(principal=principal, case_id=existing["id"])
        target_table = TABLES[payload["target_type"]]
        async with self._database.engine.begin() as connection:
            target = (
                (
                    await connection.execute(
                        text(
                            f"SELECT * FROM {target_table} WHERE tenant_id=:tenant AND space_id=:space AND id=:id"  # noqa: S608
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "id": payload["target_id"],
                        },
                    )
                )
                .mappings()
                .first()
            )  # noqa: S608
            if target is None:
                raise ApiProblem(
                    404,
                    "REVIEW_TARGET_NOT_FOUND",
                    "Review target unavailable",
                    "The draft target is unavailable.",
                )
            await DerivedReadGate(connection, principal, space_id, self.record_denial).require(
                payload["target_type"], payload["target_id"]
            )
            case_id, now = new_uuid7(), datetime.now(UTC)
            try:
                await connection.execute(
                    text(
                        "INSERT INTO review_cases (id,tenant_id,space_id,workflow_task_id,policy_id,target_type,target_id,risk_level,status,current_stage,reason,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:workflow,:policy,:type,:target,:risk,'OPEN',:stage,:reason,:now,:actor,:now,:actor)"
                    ),
                    {
                        "id": case_id,
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "workflow": workflow_task_id,
                        "policy": payload["policy_id"],
                        "type": payload["target_type"],
                        "target": payload["target_id"],
                        "risk": payload["risk_level"],
                        "stage": policy["stages"][0],
                        "reason": payload["reason"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            except Exception as exc:
                raise ApiProblem(
                    409,
                    "REVIEW_ALREADY_OPEN",
                    "Review already exists",
                    "A review case already exists for this target.",
                ) from exc
            await connection.execute(
                text(
                    "INSERT INTO review_deliveries (id,review_case_id,kind,payload,created_at) VALUES (:id,:case,'START',CAST(:payload AS jsonb),:now)"
                ),
                {
                    "id": new_uuid7(),
                    "case": case_id,
                    "now": now,
                    "payload": json.dumps(
                        {
                            "workflow_type": "HUMAN_REVIEW",
                            "task_id": str(workflow_task_id),
                            "review_case_id": str(case_id),
                            "actor_id": str(principal.actor_id),
                            "trace_id": trace_id,
                            "approval_timeout_seconds": int(policy["timeout_seconds"]),
                        }
                    ),
                },
            )
            await record_revision(
                connection, case_id, content(target), 1, UUID(str(target["created_by"])), None, now
            )
            for sequence, stage in enumerate(policy["stages"], start=1):
                await connection.execute(
                    text(
                        "INSERT INTO review_tasks (id,review_case_id,stage,sequence,status,due_at,created_at,updated_at) VALUES (:id,:case,:stage,:sequence,:status,:due,:now,:now)"
                    ),
                    {
                        "id": new_uuid7(),
                        "case": case_id,
                        "stage": stage,
                        "sequence": sequence,
                        "status": "PENDING" if sequence == 1 else "PENDING",
                        "due": now + timedelta(seconds=int(policy["timeout_seconds"]) * sequence),
                        "now": now,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="review.create",
                resource_type="ReviewCase",
                resource_id=case_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "target_type": payload["target_type"],
                    "target_id": str(payload["target_id"]),
                    "workflow_task_id": str(workflow_task_id),
                },
            )
        return await self.get_review_case(principal=principal, case_id=case_id)

    async def get_review_case(self, *, principal: Principal, case_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            case = (
                (
                    await connection.execute(
                        text(
                            "SELECT rc.*,wt.workflow_id FROM review_cases rc JOIN workflow_tasks wt ON wt.id=rc.workflow_task_id WHERE rc.tenant_id=:tenant AND rc.id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": case_id},
                    )
                )
                .mappings()
                .first()
            )
            if case is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Review case unavailable",
                    "The review case is unavailable.",
                )
            principal = await self.principal_for_space(
                principal=principal, space_id=UUID(str(case["space_id"])), action="review.read"
            )
            await DerivedReadGate(
                connection, principal, UUID(str(case["space_id"])), self.record_denial
            ).require(case["target_type"], case["target_id"])
            target_context = await self._review_context(
                connection,
                principal,
                UUID(str(case["space_id"])),
                case["target_type"],
                case["target_id"],
            )
            actions = (
                (
                    await connection.execute(
                        text(
                            "SELECT ra.*,rt.stage FROM review_actions ra JOIN review_tasks rt ON rt.id=ra.review_task_id WHERE ra.review_case_id=:id ORDER BY ra.created_at"
                        ),
                        {"id": case_id},
                    )
                )
                .mappings()
                .all()
            )
            revisions = (
                (
                    await connection.execute(
                        text(
                            "SELECT revision,content_snapshot,content_checksum,original_author_id,edited_by,created_at "
                            "FROM review_target_revisions WHERE review_case_id=:id ORDER BY revision"
                        ),
                        {"id": case_id},
                    )
                )
                .mappings()
                .all()
            )
            pending_delivery = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM review_deliveries WHERE review_case_id=:id AND delivered_at IS NULL"
                    ),
                    {"id": case_id},
                )
            ).scalar_one()
            tasks = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,stage,status,assignee_id,claimed_by,due_at,escalation_count FROM review_tasks WHERE review_case_id=:case ORDER BY sequence"
                        ),
                        {"case": case_id},
                    )
                )
                .mappings()
                .all()
            )
            actor_ids = {case["created_by"], case["updated_by"]}
            for revision in revisions:
                actor_ids.add(revision["original_author_id"])
                if revision["edited_by"]:
                    actor_ids.add(revision["edited_by"])
            actor_ids.update(action["created_by"] for action in actions)
            actor_ids.update(task["claimed_by"] for task in tasks if task["claimed_by"])
            labels = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,display_name FROM user_identities WHERE tenant_id=:tenant AND id IN :ids"
                        ).bindparams(bindparam("ids", expanding=True)),
                        {"tenant": principal.tenant_id, "ids": list(actor_ids)},
                    )
                )
                .mappings()
                .all()
            )
        value = _json_value(case)
        value["workflow_delivery_status"] = "PENDING" if pending_delivery else "DELIVERED"
        value["content_revisions"] = [_json_value(r) for r in revisions]
        value["tasks"] = [_json_value(task) for task in tasks]
        value["target_context"] = target_context
        value["actions"] = [_json_value(action) for action in actions]
        value["actor_labels"] = {str(item["id"]): item["display_name"] for item in labels}
        return value

    async def list_review_cases(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM review_cases WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .scalars()
                .all()
            )
        visible = []
        for item in ids:
            try:
                visible.append(
                    await self.get_review_case(principal=principal, case_id=UUID(str(item)))
                )
            except ApiProblem as exc:
                if exc.status != 404:
                    raise
        return visible

    async def restart_review_case(
        self,
        *,
        principal: Principal,
        case_id: UUID,
        reason: str,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        case = await self.get_review_case(principal=principal, case_id=case_id)
        principal = await self.principal_for_space(
            principal=principal, space_id=UUID(str(case["space_id"])), action="review.create"
        )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            current = (
                (
                    await connection.execute(
                        text(
                            "SELECT rc.*,rp.timeout_seconds FROM review_cases rc JOIN review_policies rp ON rp.id=rc.policy_id "
                            "WHERE rc.id=:id AND rc.tenant_id=:tenant FOR UPDATE OF rc"
                        ),
                        {"id": case_id, "tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .one()
            )
            if current["status"] not in {"OPEN", "WAITING_EVIDENCE", "OVERDUE"}:
                raise ApiProblem(
                    409,
                    "REVIEW_NOT_RESTARTABLE",
                    "Review cannot restart",
                    "Completed reviews stay immutable.",
                )
            value = await load_target(connection, current)
            previous = (
                (
                    await connection.execute(
                        text(
                            "SELECT revision,original_author_id FROM review_target_revisions "
                            "WHERE review_case_id=:id ORDER BY revision DESC LIMIT 1"
                        ),
                        {"id": case_id},
                    )
                )
                .mappings()
                .first()
            )
            now = datetime.now(UTC)
            await record_revision(
                connection,
                case_id,
                value,
                int(previous["revision"]) + 1 if previous else 1,
                previous["original_author_id"] if previous else UUID(value["created_by"]),
                None,  # Rebinding is audited separately; it is not a material content edit.
                now,
            )
            await connection.execute(
                text(
                    "UPDATE review_tasks SET status='PENDING',claimed_by=NULL,assignee_id=NULL,updated_at=:now WHERE review_case_id=:id"
                ),
                {"id": case_id, "now": now},
            )
            await connection.execute(
                text(
                    "UPDATE review_cases SET status='OPEN',current_stage='ENGINEERING',updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"id": case_id, "now": now, "actor": principal.actor_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO review_deliveries (id,review_case_id,kind,payload,created_at) "
                    "VALUES (:id,:case,'START',CAST(:payload AS jsonb),:now) ON CONFLICT (review_case_id,kind) DO NOTHING"
                ),
                {
                    "id": new_uuid7(),
                    "case": case_id,
                    "now": now,
                    "payload": json.dumps(
                        {
                            "workflow_type": "HUMAN_REVIEW",
                            "task_id": str(current["workflow_task_id"]),
                            "review_case_id": str(case_id),
                            "actor_id": str(principal.actor_id),
                            "trace_id": trace_id,
                            "approval_timeout_seconds": int(current["timeout_seconds"]),
                        }
                    ),
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="review.restart",
                resource_type="ReviewCase",
                resource_id=case_id,
                space_id=UUID(str(current["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"reason": reason, "version_reset": True},
            )
            return {"case_id": str(case_id)}

        await self._idempotent(
            principal=principal,
            operation=f"review.restart:{case_id}",
            key=idempotency_key,
            request={"reason": reason},
            mutation=mutation,
        )
        return await self.get_review_case(principal=principal, case_id=case_id)

    async def act_on_review(
        self,
        *,
        principal: Principal,
        case_id: UUID,
        task_id: UUID,
        payload: dict[str, Any],
        trace_id: str,
    ) -> JsonDict:
        current_case = await self.get_review_case(principal=principal, case_id=case_id)
        principal = await self.principal_for_space(
            principal=principal, space_id=UUID(str(current_case["space_id"])), action="review.act"
        )
        facts = await self.get_space_facts(UUID(str(current_case["space_id"])), principal)
        async with self._database.engine.begin() as connection:
            case = (
                (
                    await connection.execute(
                        text(
                            "SELECT rc.*,rp.stages FROM review_cases rc JOIN review_policies rp ON rp.id=rc.policy_id WHERE rc.tenant_id=:tenant AND rc.id=:case FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "case": case_id},
                    )
                )
                .mappings()
                .first()
            )
            task = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM review_tasks WHERE id=:task AND review_case_id=:case FOR UPDATE"
                        ),
                        {"task": task_id, "case": case_id},
                    )
                )
                .mappings()
                .first()
            )
            if case is None or task is None or task["stage"] != case["current_stage"]:
                raise ApiProblem(
                    409,
                    "REVIEW_TASK_NOT_ACTIVE",
                    "Review task is not active",
                    "Reload the review case before acting.",
                )
            try:
                validate_stage_role(
                    ReviewStage(task["stage"]), facts.member_roles | principal.tenant_roles
                )
            except ReviewRuleViolation as exc:
                raise ApiProblem(403, exc.code, "Stage role required", str(exc)) from exc
            revision = await checked_revision(connection, case)
            if task["assignee_id"] not in (None, principal.actor_id):
                raise ApiProblem(
                    409, "REVIEW_TASK_ASSIGNED", "Task assigned", "Acting user is not the assignee."
                )
            now, decision = datetime.now(UTC), ReviewDecision(payload["decision"])
            if task["claimed_by"] not in (None, principal.actor_id):
                raise ApiProblem(
                    409,
                    "REVIEW_TASK_CLAIMED",
                    "Review task claimed",
                    "The task is claimed by another reviewer.",
                )
            if not str(payload["reason"]).strip():
                raise ApiProblem(
                    422, "REVIEW_REASON_REQUIRED", "Reason required", "Explain the decision."
                )
            after_content = revision["content_snapshot"]
            if decision is ReviewDecision.MODIFY:
                after_content = await modify_target(
                    connection, case, payload.get("change_set", {}), principal.actor_id, now
                )
            elif payload.get("change_set"):
                raise ApiProblem(
                    422,
                    "REVIEW_CHANGE_SET_INVALID",
                    "Edit requires MODIFY",
                    "Use MODIFY for content changes.",
                )
            before = {
                "case_status": case["status"],
                "task_status": task["status"],
                "target_id": str(case["target_id"]),
                "content": revision["content_snapshot"],
                "content_checksum": revision["content_checksum"],
            }
            await connection.execute(
                text(
                    "UPDATE review_tasks SET claimed_by=:actor,status='CLAIMED',updated_at=:now WHERE id=:id"
                ),
                {"actor": principal.actor_id, "now": now, "id": task_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO review_actions (id,review_case_id,review_task_id,decision,reason,change_set,before_snapshot,after_snapshot,created_at,created_by) VALUES (:id,:case,:task,:decision,:reason,CAST(:changes AS jsonb),CAST(:before AS jsonb),CAST(:after AS jsonb),:now,:actor)"
                ),
                {
                    "id": new_uuid7(),
                    "case": case_id,
                    "task": task_id,
                    "decision": decision.value,
                    "reason": payload["reason"],
                    "changes": json.dumps(payload.get("change_set", {})),
                    "before": json.dumps(before),
                    "after": json.dumps({"decision": decision.value, "content": after_content}),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            if decision is ReviewDecision.REQUEST_EVIDENCE:
                await connection.execute(
                    text(
                        "UPDATE review_tasks SET status='WAITING_EVIDENCE',updated_at=:now WHERE id=:id"
                    ),
                    {"now": now, "id": task_id},
                )
                await connection.execute(
                    text(
                        "UPDATE review_cases SET status='WAITING_EVIDENCE',updated_at=:now,updated_by=:actor WHERE id=:id"
                    ),
                    {"now": now, "actor": principal.actor_id, "id": case_id},
                )
            elif decision is ReviewDecision.REJECT:
                await connection.execute(
                    text("UPDATE review_tasks SET status='REJECTED',updated_at=:now WHERE id=:id"),
                    {"now": now, "id": task_id},
                )
                await connection.execute(
                    text(
                        "UPDATE review_cases SET status='REJECTED',current_stage=NULL,updated_at=:now,updated_by=:actor WHERE id=:id"
                    ),
                    {"now": now, "actor": principal.actor_id, "id": case_id},
                )
            elif decision is ReviewDecision.TRANSFER:
                if payload.get("assignee_id") is None:
                    raise ApiProblem(
                        422,
                        "REVIEW_TRANSFER_ASSIGNEE_REQUIRED",
                        "Assignee required",
                        "Transfer requires an assignee.",
                    )
                await connection.execute(
                    text(
                        "UPDATE review_tasks SET assignee_id=:assignee,claimed_by=NULL,status='PENDING',updated_at=:now WHERE id=:id"
                    ),
                    {"assignee": payload["assignee_id"], "now": now, "id": task_id},
                )
            else:
                await self._advance_review(connection, principal, case, task, decision, now)
            final_status = (
                await connection.execute(
                    text("SELECT status FROM review_cases WHERE id=:id"), {"id": case_id}
                )
            ).scalar_one()
            if final_status in {"APPROVED", "REJECTED"}:
                await connection.execute(
                    text(
                        "INSERT INTO review_deliveries (id,review_case_id,kind,payload,created_at) VALUES (:id,:case,'DECISION',CAST(:payload AS jsonb),:now) ON CONFLICT (review_case_id,kind) DO NOTHING"
                    ),
                    {
                        "id": new_uuid7(),
                        "case": case_id,
                        "now": now,
                        "payload": json.dumps(
                            {
                                "action": "APPROVE" if final_status == "APPROVED" else "REJECT",
                                "actor_id": str(principal.actor_id),
                                "reason": payload["reason"],
                            }
                        ),
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="review.act",
                resource_type="ReviewCase",
                resource_id=case_id,
                space_id=UUID(str(case["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"decision": decision.value, "task_id": str(task_id)},
            )
        return await self.get_review_case(principal=principal, case_id=case_id)

    async def _advance_review(
        self,
        connection: AsyncConnection,
        principal: Principal,
        case: Any,
        task: Any,
        decision: ReviewDecision,
        now: datetime,
    ) -> None:
        if decision is ReviewDecision.MODIFY:
            await connection.execute(
                text(
                    "UPDATE review_tasks SET status='PENDING',claimed_by=NULL,updated_at=:now WHERE review_case_id=:id"
                ),
                {"now": now, "id": case["id"]},
            )
            await connection.execute(
                text(
                    "UPDATE review_cases SET current_stage='ENGINEERING',status='OPEN',updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"id": case["id"], "now": now, "actor": principal.actor_id},
            )
            return
        if task["stage"] == "APPROVAL":
            revision = await checked_revision(connection, case)
            editors = (
                (
                    await connection.execute(
                        text(
                            "SELECT edited_by FROM review_target_revisions WHERE review_case_id=:id AND edited_by IS NOT NULL"
                        ),
                        {"id": case["id"]},
                    )
                )
                .scalars()
                .all()
            )
            prior_ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT ra.created_by FROM review_actions ra JOIN review_tasks rt ON rt.id=ra.review_task_id WHERE ra.review_case_id=:case AND rt.stage <> 'APPROVAL' AND ra.decision='ACCEPT'"
                        ),
                        {"case": case["id"]},
                    )
                )
                .scalars()
                .all()
            )
            try:
                validate_final_approval_separation(
                    risk=RiskLevel(case["risk_level"]),
                    creator_id=UUID(str(revision["original_author_id"])),
                    editor_ids=[UUID(str(item)) for item in editors],
                    reviewer_ids=[UUID(str(item)) for item in prior_ids if item],
                    approver_id=principal.actor_id,
                )
            except ReviewRuleViolation as exc:
                raise ApiProblem(409, exc.code, "Duty separation rejected", str(exc)) from exc
            await self._promote_target(connection, principal, case, now)
            await connection.execute(
                text("UPDATE review_tasks SET status='APPROVED',updated_at=:now WHERE id=:id"),
                {"now": now, "id": task["id"]},
            )
            await connection.execute(
                text(
                    "UPDATE review_cases SET status='APPROVED',current_stage=NULL,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"now": now, "actor": principal.actor_id, "id": case["id"]},
            )
            return
        await connection.execute(
            text("UPDATE review_tasks SET status='APPROVED',updated_at=:now WHERE id=:id"),
            {"now": now, "id": task["id"]},
        )
        next_task = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM review_tasks WHERE review_case_id=:case AND sequence=:sequence FOR UPDATE"
                    ),
                    {"case": case["id"], "sequence": int(task["sequence"]) + 1},
                )
            )
            .mappings()
            .first()
        )
        if next_task is None:
            await self._promote_target(connection, principal, case, now)
            await connection.execute(
                text(
                    "UPDATE review_cases SET status='APPROVED',current_stage=NULL,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"now": now, "actor": principal.actor_id, "id": case["id"]},
            )
        else:
            await connection.execute(
                text(
                    "UPDATE review_cases SET current_stage=:stage,status='OPEN',updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "stage": next_task["stage"],
                    "now": now,
                    "actor": principal.actor_id,
                    "id": case["id"],
                },
            )

    async def _promote_target(
        self, connection: AsyncConnection, principal: Principal, case: Any, now: datetime
    ) -> None:
        await checked_revision(connection, case)
        await DerivedReadGate(
            connection, principal, UUID(str(case["space_id"])), self.record_denial
        ).require(case["target_type"], case["target_id"])
        if case["target_type"] == "WIKI_PAGE_VERSION":
            context = await self._review_context(
                connection,
                principal,
                UUID(str(case["space_id"])),
                "WIKI_PAGE_VERSION",
                case["target_id"],
            )
            if not context["evidence"] or any(
                item["anchor_status"] != "VALID" for item in context["evidence"]
            ):
                raise ApiProblem(
                    409,
                    "REVIEW_EVIDENCE_REQUIRED",
                    "Evidence required",
                    "Review the page against current source anchors before approval.",
                )
            # ReviewCase is the authoritative approval fact. The Wiki version row
            # and its status remain immutable, including pre-existing history.
            return
        if case["target_type"] == "RELATION_CANDIDATE":
            evidence = (
                (
                    await connection.execute(
                        text(
                            "SELECT ec.stance,sa.status AS anchor_status FROM evidence_candidates ec "
                            "JOIN source_anchors sa ON sa.id=ec.source_anchor_id "
                            "WHERE ec.relation_candidate_id=:id"
                        ),
                        {"id": case["target_id"]},
                    )
                )
                .mappings()
                .all()
            )
            try:
                validate_evidence_gate(
                    has_valid_evidence=any(
                        item["anchor_status"] == "VALID" and item["stance"] == "SUPPORTS"
                        for item in evidence
                    )
                )
            except ReviewRuleViolation as exc:
                raise ApiProblem(409, exc.code, "Evidence required", str(exc)) from exc
            candidate = (
                (
                    await connection.execute(
                        text("SELECT * FROM candidate_relations WHERE id=:id FOR SHARE"),
                        {"id": case["target_id"]},
                    )
                )
                .mappings()
                .one()
            )
            relation_id = new_uuid7()
            relation_definition = (
                await connection.execute(
                    text(
                        "SELECT definition FROM relation_types WHERE schema_version_id=:schema "
                        "AND relation_type_key=:key"
                    ),
                    {
                        "schema": candidate["schema_version_id"],
                        "key": candidate["relation_type_key"],
                    },
                )
            ).scalar_one_or_none() or {}
            await connection.execute(
                text(
                    "INSERT INTO relations (id,tenant_id,space_id,candidate_id,schema_version_id,"
                    "relation_type_key,source_entity_id,target_entity_id,is_causal,status,provenance,"
                    "created_at,created_by) VALUES (:id,:tenant,:space,:candidate,:schema,:key,:source,"
                    ":target,:causal,'APPROVED',CAST(:provenance AS jsonb),:now,:actor)"
                ),
                {
                    "id": relation_id,
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "candidate": candidate["id"],
                    "schema": candidate["schema_version_id"],
                    "key": candidate["relation_type_key"],
                    "source": candidate["source_entity_id"],
                    "target": candidate["target_entity_id"],
                    "causal": bool(dict(relation_definition).get("causal", False)),
                    "provenance": json.dumps(
                        {**dict(candidate["provenance"]), "review_case_id": str(case["id"])}
                    ),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            evidence_rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT ec.*,sa.status AS anchor_status,sd.source_level FROM evidence_candidates ec "
                            "JOIN source_anchors sa ON sa.id=ec.source_anchor_id "
                            "JOIN source_versions sv ON sv.id=sa.source_version_id "
                            "JOIN source_documents sd ON sd.id=sv.source_document_id "
                            "WHERE ec.relation_candidate_id=:id"
                        ),
                        {"id": candidate["id"]},
                    )
                )
                .mappings()
                .all()
            )
            for item in evidence_rows:
                await connection.execute(
                    text(
                        "INSERT INTO evidence_records (id,tenant_id,space_id,relation_id,"
                        "source_anchor_id,stance,excerpt_hash,source_authority,screenshot_ref,status,"
                        "created_at,created_by) VALUES (:id,:tenant,:space,:relation,:anchor,:stance,"
                        ":excerpt,:authority,'{}'::jsonb,:status,:now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": candidate["tenant_id"],
                        "space": candidate["space_id"],
                        "relation": relation_id,
                        "anchor": item["source_anchor_id"],
                        "stance": item["stance"],
                        "excerpt": item["excerpt_hash"],
                        "authority": item["source_level"],
                        "status": "ACCEPTED" if item["anchor_status"] == "VALID" else "STALE",
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            return
        if case["target_type"] != "CLAIM_CANDIDATE":
            return
        candidate = (
            (
                await connection.execute(
                    text("SELECT * FROM claim_candidates WHERE id=:id FOR SHARE"),
                    {"id": case["target_id"]},
                )
            )
            .mappings()
            .one()
        )
        evidence = (
            (
                await connection.execute(
                    text(
                        "SELECT ec.*,sa.status AS anchor_status,sd.source_level FROM evidence_candidates ec JOIN source_anchors sa ON sa.id=ec.source_anchor_id JOIN source_versions sv ON sv.id=sa.source_version_id JOIN source_documents sd ON sd.id=sv.source_document_id WHERE ec.claim_candidate_id=:id"
                    ),
                    {"id": candidate["id"]},
                )
            )
            .mappings()
            .all()
        )
        try:
            validate_evidence_gate(
                has_valid_evidence=any(
                    item["anchor_status"] == "VALID" and item["stance"] == "SUPPORTS"
                    for item in evidence
                )
            )
        except ReviewRuleViolation as exc:
            raise ApiProblem(409, exc.code, "Evidence required", str(exc)) from exc
        claim_id = new_uuid7()
        await connection.execute(
            text(
                "INSERT INTO claims (id,tenant_id,space_id,candidate_id,subject_entity_id,predicate_key,object_value,statement,scope,confidence_level,status,provenance,created_at,created_by) VALUES (:id,:tenant,:space,:candidate,:subject,:predicate,CAST(:object AS jsonb),:statement,'{}'::jsonb,:risk,'APPROVED',CAST(:provenance AS jsonb),:now,:actor)"
            ),
            {
                "id": claim_id,
                "tenant": candidate["tenant_id"],
                "space": candidate["space_id"],
                "candidate": candidate["id"],
                "subject": candidate["subject_entity_id"],
                "predicate": candidate["predicate_key"],
                "object": json.dumps(candidate["object_value"]),
                "statement": candidate["statement"],
                "risk": case["risk_level"],
                "provenance": json.dumps(
                    {**dict(candidate["provenance"]), "review_case_id": str(case["id"])}
                ),
                "now": now,
                "actor": principal.actor_id,
            },
        )
        for item in evidence:
            await connection.execute(
                text(
                    "INSERT INTO evidence_records (id,tenant_id,space_id,claim_id,source_anchor_id,stance,excerpt_hash,source_authority,screenshot_ref,status,created_at,created_by) VALUES (:id,:tenant,:space,:claim,:anchor,:stance,:excerpt,:authority,'{}'::jsonb,:status,:now,:actor)"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "claim": claim_id,
                    "anchor": item["source_anchor_id"],
                    "stance": item["stance"],
                    "excerpt": item["excerpt_hash"],
                    "authority": item["source_level"],
                    "status": "ACCEPTED" if item["anchor_status"] == "VALID" else "STALE",
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
        await connection.execute(
            text(
                "UPDATE claim_candidates SET status='REJECTED' WHERE id=:id AND status='NEEDS_EVIDENCE'"
            ),
            {"id": candidate["id"]},
        )

    async def list_conflicts(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM conflict_cases WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        visible = []
        for row in rows:
            try:
                visible.append(await self.get_conflict(principal=principal, conflict_id=row["id"]))
            except ApiProblem as exc:
                if exc.status != 404:
                    raise
        return visible

    async def materialize_conflicts(
        self, *, principal: Principal, space_id: UUID, trace_id: str
    ) -> list[JsonDict]:
        """Promote M5 detection facts into clustered M6 cases without losing candidates."""
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM knowledge_spaces WHERE id=:id FOR NO KEY UPDATE"),
                {"id": space_id},
            )
            candidates = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM conflict_candidates WHERE tenant_id=:tenant "
                            "AND space_id=:space AND status='OPEN' FOR SHARE"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
            for candidate in candidates:
                details = dict(candidate["details"])
                cluster_key = (
                    f"{candidate['code']}:{details.get('left_claim_candidate_id', candidate['id'])}:"
                    f"{details.get('right_claim_candidate_id', candidate['object_id'])}"
                )
                existing = (
                    await connection.execute(
                        text(
                            "SELECT id FROM conflict_cases WHERE space_id=:space "
                            "AND cluster_key=:cluster FOR UPDATE"
                        ),
                        {"space": space_id, "cluster": cluster_key},
                    )
                ).scalar_one_or_none()
                case_id = UUID(str(existing)) if existing else new_uuid7()
                if existing is None:
                    await connection.execute(
                        text(
                            "INSERT INTO conflict_cases "
                            "(id,tenant_id,space_id,cluster_key,kind,severity,blocking,status,"
                            "suggested_action,details,created_by) VALUES "
                            "(:id,:tenant,:space,:cluster,:kind,:severity,:blocking,'OPEN',"
                            "'COMPARE_EVIDENCE',CAST(:details AS jsonb),:actor)"
                        ),
                        {
                            "id": case_id,
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "cluster": cluster_key,
                            "kind": candidate["code"],
                            "severity": candidate["severity"],
                            "blocking": candidate["severity"] == "BLOCKING",
                            "details": json.dumps(details),
                            "actor": principal.actor_id,
                        },
                    )
                for side, object_id in (
                    ("A", details.get("left_claim_candidate_id")),
                    ("B", details.get("right_claim_candidate_id", candidate["object_id"])),
                ):
                    if object_id is None:
                        continue
                    await connection.execute(
                        text(
                            "INSERT INTO conflict_items "
                            "(id,conflict_case_id,side,object_type,object_id,evidence_snapshot) "
                            "VALUES (:id,:case,:side,'CLAIM_CANDIDATE',:object,CAST(:snapshot AS jsonb)) "
                            "ON CONFLICT (conflict_case_id,object_type,object_id) DO NOTHING"
                        ),
                        {
                            "id": new_uuid7(),
                            "case": case_id,
                            "side": side,
                            "object": object_id,
                            "snapshot": json.dumps(details),
                        },
                    )
                await connection.execute(
                    text("UPDATE conflict_candidates SET status='ACKNOWLEDGED' WHERE id=:id"),
                    {"id": candidate["id"]},
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="conflict.detect",
                resource_type="ConflictCase",
                resource_id=None,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"candidates": len(candidates)},
            )
        return await self.list_conflicts(principal=principal, space_id=space_id)

    async def get_conflict(self, *, principal: Principal, conflict_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM conflict_cases WHERE tenant_id=:tenant AND id=:id"),
                        {"tenant": principal.tenant_id, "id": conflict_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Conflict unavailable",
                "The conflict is unavailable.",
            )
        principal = await self.principal_for_space(
            principal=principal, space_id=UUID(str(row["space_id"])), action="conflict.read"
        )
        async with self._database.engine.connect() as connection:
            items = (
                (
                    await connection.execute(
                        text(
                            "SELECT side,object_type,object_id FROM conflict_items WHERE conflict_case_id=:id ORDER BY side"
                        ),
                        {"id": conflict_id},
                    )
                )
                .mappings()
                .all()
            )
            if not items:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Conflict unavailable", "Conflict unavailable."
                )
            gate = DerivedReadGate(
                connection, principal, UUID(str(row["space_id"])), self.record_denial
            )
            for item in items:
                await gate.require(item["object_type"], item["object_id"])
            contexts = [
                {
                    "side": item["side"],
                    **await self._review_context(
                        connection,
                        principal,
                        UUID(str(row["space_id"])),
                        item["object_type"],
                        item["object_id"],
                    ),
                }
                for item in items
            ]
            decisions = (
                (
                    await connection.execute(
                        text(
                            "SELECT resolution,reason,conditions,created_at,created_by FROM conflict_decisions WHERE conflict_case_id=:id ORDER BY created_at"
                        ),
                        {"id": conflict_id},
                    )
                )
                .mappings()
                .all()
            )
        return _json_value(
            {**dict(row), "items": contexts, "decisions": [dict(d) for d in decisions]}
        )

    async def resolve_conflict(
        self, *, principal: Principal, conflict_id: UUID, payload: dict[str, Any], trace_id: str
    ) -> JsonDict:
        current = await self.get_conflict(principal=principal, conflict_id=conflict_id)
        await self.principal_for_space(
            principal=principal, space_id=UUID(current["space_id"]), action="conflict.resolve"
        )
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM knowledge_spaces WHERE id=:space FOR NO KEY UPDATE"),
                {"space": UUID(current["space_id"])},
            )
            case = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM conflict_cases WHERE tenant_id=:tenant AND id=:id FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": conflict_id},
                    )
                )
                .mappings()
                .first()
            )
            if case is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Conflict unavailable",
                    "The conflict is unavailable.",
                )
            items = (
                (
                    await connection.execute(
                        text(
                            "SELECT side,object_type,object_id,evidence_snapshot FROM conflict_items WHERE conflict_case_id=:id ORDER BY side"
                        ),
                        {"id": conflict_id},
                    )
                )
                .mappings()
                .all()
            )
            resolution = ConflictResolution(payload["resolution"])
            status = (
                "OPEN"
                if resolution is ConflictResolution.REOPEN
                else (
                    "UNRESOLVED"
                    if resolution is ConflictResolution.UNRESOLVED
                    else ("EXPIRED" if resolution is ConflictResolution.EXPIRED else "RESOLVED")
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO conflict_decisions (id,conflict_case_id,resolution,reason,conditions,comparison_snapshot,created_at,created_by) VALUES (:id,:case,:resolution,:reason,CAST(:conditions AS jsonb),CAST(:snapshot AS jsonb),:now,:actor)"
                ),
                {
                    "id": new_uuid7(),
                    "case": conflict_id,
                    "resolution": resolution.value,
                    "reason": payload["reason"],
                    "conditions": json.dumps(payload.get("conditions", {})),
                    "snapshot": json.dumps([_json_value(item) for item in items]),
                    "now": datetime.now(UTC),
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text("UPDATE conflict_cases SET status=:status WHERE id=:id"),
                {"status": status, "id": conflict_id},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="conflict.resolve",
                resource_type="ConflictCase",
                resource_id=conflict_id,
                space_id=UUID(str(case["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"resolution": resolution.value},
            )
        return _json_value({**dict(case), "status": status})

    async def review_quality_stats(self, *, principal: Principal, space_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT count(*) AS total_cases, count(*) FILTER (WHERE status='APPROVED') AS approved_cases, count(*) FILTER (WHERE status='REJECTED') AS rejected_cases, (SELECT count(*) FROM review_actions ra JOIN review_cases rc ON rc.id=ra.review_case_id WHERE rc.tenant_id=:tenant AND rc.space_id=:space AND ra.decision='MODIFY') AS modifications, (SELECT count(*) FROM conflict_cases WHERE tenant_id=:tenant AND space_id=:space AND status='UNRESOLVED') AS disputes FROM review_cases WHERE tenant_id=:tenant AND space_id=:space"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .one()
            )
        return _json_value(row)
