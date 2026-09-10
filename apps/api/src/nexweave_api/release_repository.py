"""M7 PostgreSQL quality, immutable Release, retrieval, graph and query service."""
# ruff: noqa: E501, S608

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import JsonDict, _json_value
from nexweave_api.review_repository import ReviewRepository
from nexweave_domain import (
    Principal,
    ReleaseGate,
    ReleaseRuleViolation,
    new_uuid7,
    reciprocal_rank_fusion,
    release_manifest_checksum,
    validate_release_approver,
    validate_release_gate,
    validate_release_version,
)

CLASSIFICATION_LEVEL = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "HIGHLY_RESTRICTED": 3}


class ReleaseRepository(ReviewRepository):
    async def create_evaluation_suite(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        suite_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            schema = (
                await connection.execute(
                    text(
                        "SELECT id FROM schema_versions WHERE tenant_id=:tenant AND space_id=:space "
                        "AND id=:schema AND status='PUBLISHED'"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "schema": payload["schema_version_id"],
                    },
                )
            ).scalar_one_or_none()
            if schema is None:
                raise ApiProblem(
                    409,
                    "EVALUATION_SCHEMA_NOT_PUBLISHED",
                    "Evaluation Schema unavailable",
                    "EvaluationSuite requires a published SchemaVersion in the same space.",
                )
            await connection.execute(
                text(
                    "INSERT INTO evaluation_suites (id,tenant_id,space_id,schema_version_id,suite_key,definition,version,name,minimum_pass_rate,status,created_at,created_by) SELECT :id,:tenant,:space,sv.id,:key,CAST(:definition AS jsonb),:version,:name,:rate,'ACTIVE',:now,:actor FROM schema_versions sv WHERE sv.tenant_id=:tenant AND sv.space_id=:space AND sv.id=:schema AND sv.status='PUBLISHED'"
                ),
                {
                    "id": suite_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": payload["schema_version_id"],
                    "key": payload["suite_key"],
                    "definition": json.dumps(
                        {
                            "cases": payload["cases"],
                            "minimum_pass_rate": payload["minimum_pass_rate"],
                        }
                    ),
                    "version": payload["version"],
                    "name": payload["name"],
                    "rate": payload["minimum_pass_rate"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            for item in payload["cases"]:
                await connection.execute(
                    text(
                        "INSERT INTO evaluation_cases (id,suite_id,case_key,case_type,question,expected_claim_ids,expected_terms,expect_refusal,metadata,created_at) VALUES (:id,:suite,:key,:type,:question,:claims,:terms,:refusal,CAST(:metadata AS jsonb),:now)"
                    ),
                    {
                        "id": new_uuid7(),
                        "suite": suite_id,
                        "key": item["case_key"],
                        "type": item["case_type"],
                        "question": item["question"],
                        "claims": [
                            UUID(str(value)) for value in item.get("expected_claim_ids", [])
                        ],
                        "terms": list(item.get("expected_terms", [])),
                        "refusal": item.get("expect_refusal", False),
                        "metadata": json.dumps(item.get("metadata", {})),
                        "now": now,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="quality.suite.create",
                resource_type="EvaluationSuite",
                resource_id=suite_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"suite_key": payload["suite_key"], "version": payload["version"]},
            )
            suite = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,tenant_id,space_id,schema_version_id,suite_key,version,name,minimum_pass_rate,status,created_at,created_by FROM evaluation_suites WHERE id=:id"
                        ),
                        {"id": suite_id},
                    )
                )
                .mappings()
                .one()
            )
            cases = (
                (
                    await connection.execute(
                        text(
                            "SELECT case_key,case_type,question,expected_claim_ids,expected_terms,expect_refusal,metadata FROM evaluation_cases WHERE suite_id=:id ORDER BY case_key"
                        ),
                        {"id": suite_id},
                    )
                )
                .mappings()
                .all()
            )
            return _json_value({**suite, "cases": [dict(item) for item in cases]})

        return await self._idempotent(
            principal=principal,
            operation=f"quality.suite.create:{space_id}",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def get_evaluation_suite(self, *, principal: Principal, suite_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            suite = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,tenant_id,space_id,schema_version_id,suite_key,version,name,minimum_pass_rate,status,created_at,created_by FROM evaluation_suites WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": suite_id},
                    )
                )
                .mappings()
                .first()
            )
            if suite is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Evaluation suite unavailable",
                    "The EvaluationSuite is unavailable.",
                )
            cases = (
                (
                    await connection.execute(
                        text(
                            "SELECT case_key,case_type,question,expected_claim_ids,expected_terms,expect_refusal,metadata FROM evaluation_cases WHERE suite_id=:id ORDER BY case_key"
                        ),
                        {"id": suite_id},
                    )
                )
                .mappings()
                .all()
            )
        return _json_value({**suite, "cases": [dict(item) for item in cases]})

    async def list_evaluation_suites(
        self, *, principal: Principal, space_id: UUID
    ) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM evaluation_suites WHERE tenant_id=:tenant AND space_id=:space ORDER BY suite_key,version DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .scalars()
                .all()
            )
        return [
            await self.get_evaluation_suite(principal=principal, suite_id=UUID(str(value)))
            for value in ids
        ]

    async def create_release_candidate(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        workflow_task_id: UUID,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        try:
            validate_release_version(str(payload["version"]))
        except ReleaseRuleViolation as exc:
            raise ApiProblem(422, exc.code, "Release version rejected", str(exc)) from exc
        candidate_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            locked = (
                (
                    await connection.execute(
                        text(
                            "SELECT sv.id,sv.status,sv.composition_checksum,sv.normalized_snapshot,wt.workflow_id,es.status AS suite_status FROM schema_versions sv JOIN workflow_tasks wt ON wt.tenant_id=sv.tenant_id AND wt.space_id=sv.space_id AND wt.id=:task AND wt.workflow_type='KNOWLEDGE_RELEASE' JOIN evaluation_suites es ON es.tenant_id=sv.tenant_id AND es.space_id=sv.space_id AND es.id=:suite JOIN prompt_versions pv ON pv.tenant_id=sv.tenant_id AND pv.id=:prompt AND (pv.space_id IS NULL OR pv.space_id=sv.space_id) JOIN model_profiles mp ON mp.tenant_id=sv.tenant_id AND mp.id=:model AND (mp.space_id IS NULL OR mp.space_id=sv.space_id) WHERE sv.tenant_id=:tenant AND sv.space_id=:space AND sv.id=:schema FOR SHARE"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "schema": payload["schema_version_id"],
                            "task": workflow_task_id,
                            "suite": payload["evaluation_suite_id"],
                            "prompt": payload["prompt_version_id"],
                            "model": payload["model_profile_id"],
                        },
                    )
                )
                .mappings()
                .first()
            )
            if locked is None:
                raise ApiProblem(
                    404,
                    "RELEASE_INPUT_UNAVAILABLE",
                    "Release input unavailable",
                    "The fixed Schema, Suite, Prompt, Model or Workflow input is unavailable.",
                )
            if locked["status"] != "PUBLISHED" or locked["suite_status"] != "ACTIVE":
                raise ApiProblem(
                    409,
                    "RELEASE_INPUT_NOT_ACTIVE",
                    "Release input is not active",
                    "Release requires a published Schema and active EvaluationSuite.",
                )
            item_groups = {
                "CLAIM": sorted(set(payload.get("claim_ids", []))),
                "RELATION": sorted(set(payload.get("relation_ids", []))),
                "WIKI_PAGE_VERSION": sorted(set(payload.get("wiki_page_version_ids", []))),
            }
            manifest: dict[str, Any] = {
                "version": payload["version"],
                "schema_version_id": str(payload["schema_version_id"]),
                "composition_checksum": locked["composition_checksum"],
                "prompt_version_id": str(payload["prompt_version_id"]),
                "model_profile_id": str(payload["model_profile_id"]),
                "evaluation_suite_id": str(payload["evaluation_suite_id"]),
                "objects": {
                    key.lower(): [str(value) for value in values]
                    for key, values in item_groups.items()
                },
                "index_config": payload["index_config"],
            }
            pack_rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT spi.domain_pack_version_id,dp.pack_key,dpv.pack_version,spi.content_checksum,spi.input_order FROM schema_version_pack_inputs spi JOIN domain_pack_versions dpv ON dpv.id=spi.domain_pack_version_id JOIN domain_packs dp ON dp.id=dpv.domain_pack_id WHERE spi.schema_version_id=:schema ORDER BY spi.input_order"
                        ),
                        {"schema": payload["schema_version_id"]},
                    )
                )
                .mappings()
                .all()
            )
            manifest["pack_inputs"] = [_json_value(item) for item in pack_rows]
            evidence_rows, entity_ids, source_refs = await self._derive_manifest_refs(
                connection, principal.tenant_id, space_id, item_groups
            )
            manifest["evidence_ids"] = sorted(str(item["id"]) for item in evidence_rows)
            manifest["entity_ids"] = sorted(str(value) for value in entity_ids)
            manifest["source_refs"] = sorted(
                source_refs, key=lambda item: (item["source_version_id"], item["source_anchor_id"])
            )
            checksum = release_manifest_checksum(manifest)
            try:
                await connection.execute(
                    text(
                        "INSERT INTO release_candidates (id,tenant_id,space_id,version,schema_version_id,composition_checksum,prompt_version_id,model_profile_id,evaluation_suite_id,workflow_task_id,workflow_id,status,manifest,manifest_checksum,index_config,notes,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:version,:schema,:composition,:prompt,:model,:suite,:task,:workflow,'DRAFT',CAST(:manifest AS jsonb),:checksum,CAST(:index AS jsonb),:notes,:now,:actor,:now,:actor)"
                    ),
                    {
                        "id": candidate_id,
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "version": payload["version"],
                        "schema": payload["schema_version_id"],
                        "composition": locked["composition_checksum"],
                        "prompt": payload["prompt_version_id"],
                        "model": payload["model_profile_id"],
                        "suite": payload["evaluation_suite_id"],
                        "task": workflow_task_id,
                        "workflow": locked["workflow_id"],
                        "manifest": json.dumps(manifest),
                        "checksum": checksum,
                        "index": json.dumps(payload["index_config"]),
                        "notes": payload.get("notes", ""),
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            except Exception as exc:
                raise ApiProblem(
                    409,
                    "RELEASE_VERSION_EXISTS",
                    "Release version exists",
                    "The candidate or Release version is already reserved in this space.",
                ) from exc
            for object_type, values in item_groups.items():
                for object_id in values:
                    await connection.execute(
                        text(
                            "INSERT INTO release_candidate_items (id,candidate_id,object_type,object_id,created_at) VALUES (:id,:candidate,:type,:object,:now)"
                        ),
                        {
                            "id": new_uuid7(),
                            "candidate": candidate_id,
                            "type": object_type,
                            "object": object_id,
                            "now": now,
                        },
                    )
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.candidate.create",
                resource_type="ReleaseCandidate",
                resource_id=candidate_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": payload["version"], "manifest_checksum": checksum},
            )
            return await self._get_candidate(connection, principal.tenant_id, candidate_id)

        return await self._idempotent(
            principal=principal,
            operation=f"release.candidate.create:{space_id}",
            key=idempotency_key,
            request={**payload, "workflow_task_id": str(workflow_task_id)},
            mutation=mutation,
        )

    async def _derive_manifest_refs(
        self,
        connection: AsyncConnection,
        tenant_id: UUID,
        space_id: UUID,
        groups: dict[str, list[Any]],
    ) -> tuple[list[Any], set[UUID], list[dict[str, str]]]:
        claim_ids, relation_ids = groups["CLAIM"], groups["RELATION"]
        entity_ids: set[UUID] = set()
        if claim_ids:
            statement = text(
                "SELECT id,subject_entity_id FROM claims WHERE tenant_id=:tenant AND space_id=:space AND status='APPROVED' AND id IN :ids"
            ).bindparams(bindparam("ids", expanding=True))
            rows = (
                (
                    await connection.execute(
                        statement, {"tenant": tenant_id, "space": space_id, "ids": claim_ids}
                    )
                )
                .mappings()
                .all()
            )
            if len(rows) != len(claim_ids):
                raise ApiProblem(
                    409,
                    "RELEASE_CLAIM_NOT_APPROVED",
                    "Claim is not releasable",
                    "Every selected Claim must be approved in this space.",
                )
            entity_ids.update(UUID(str(row["subject_entity_id"])) for row in rows)
        if relation_ids:
            statement = text(
                "SELECT id,source_entity_id,target_entity_id FROM relations WHERE tenant_id=:tenant AND space_id=:space AND status='APPROVED' AND id IN :ids"
            ).bindparams(bindparam("ids", expanding=True))
            rows = (
                (
                    await connection.execute(
                        statement, {"tenant": tenant_id, "space": space_id, "ids": relation_ids}
                    )
                )
                .mappings()
                .all()
            )
            if len(rows) != len(relation_ids):
                raise ApiProblem(
                    409,
                    "RELEASE_RELATION_NOT_APPROVED",
                    "Relation is not releasable",
                    "Every selected Relation must be approved in this space.",
                )
            for row in rows:
                entity_ids.update(
                    (UUID(str(row["source_entity_id"])), UUID(str(row["target_entity_id"])))
                )
        target_ids = [*claim_ids, *relation_ids]
        if not target_ids:
            return [], entity_ids, []
        evidence = (
            (
                await connection.execute(
                    text(
                        "SELECT er.id,er.claim_id,er.relation_id,er.source_anchor_id,sa.source_version_id,sa.status AS anchor_status,sv.checksum AS source_checksum FROM evidence_records er JOIN source_anchors sa ON sa.id=er.source_anchor_id JOIN source_versions sv ON sv.id=sa.source_version_id WHERE er.tenant_id=:tenant AND er.space_id=:space AND er.status='ACCEPTED' AND (er.claim_id = ANY(:claims) OR er.relation_id = ANY(:relations))"
                    ),
                    {
                        "tenant": tenant_id,
                        "space": space_id,
                        "claims": claim_ids or [UUID(int=0)],
                        "relations": relation_ids or [UUID(int=0)],
                    },
                )
            )
            .mappings()
            .all()
        )
        covered_claims = {
            str(item["claim_id"])
            for item in evidence
            if item["claim_id"] and item["anchor_status"] == "VALID"
        }
        covered_relations = {
            str(item["relation_id"])
            for item in evidence
            if item["relation_id"] and item["anchor_status"] == "VALID"
        }
        if any(str(value) not in covered_claims for value in claim_ids) or any(
            str(value) not in covered_relations for value in relation_ids
        ):
            raise ApiProblem(
                409,
                "RELEASE_EVIDENCE_REQUIRED",
                "Release Evidence required",
                "Every selected Claim and Relation requires accepted Evidence with a VALID Anchor.",
            )
        source_refs = [
            {
                "source_version_id": str(item["source_version_id"]),
                "source_checksum": str(item["source_checksum"]),
                "source_anchor_id": str(item["source_anchor_id"]),
                "evidence_id": str(item["id"]),
            }
            for item in evidence
        ]
        return list(evidence), entity_ids, source_refs

    async def _get_candidate(
        self, connection: AsyncConnection, tenant_id: UUID, candidate_id: UUID
    ) -> JsonDict:
        row = (
            (
                await connection.execute(
                    text("SELECT * FROM release_candidates WHERE tenant_id=:tenant AND id=:id"),
                    {"tenant": tenant_id, "id": candidate_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "ReleaseCandidate unavailable",
                "The ReleaseCandidate is unavailable.",
            )
        findings = (
            (
                await connection.execute(
                    text(
                        "SELECT id,code,severity,blocking,object_type,object_id,message,details FROM release_lint_findings WHERE candidate_id=:id ORDER BY blocking DESC,severity DESC,code"
                    ),
                    {"id": candidate_id},
                )
            )
            .mappings()
            .all()
        )
        return _json_value({**row, "lint_findings": [dict(item) for item in findings]})

    async def get_release_candidate(self, *, principal: Principal, candidate_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            return await self._get_candidate(connection, principal.tenant_id, candidate_id)

    async def list_release_candidates(
        self, *, principal: Principal, space_id: UUID
    ) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM release_candidates WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .scalars()
                .all()
            )
            return [
                await self._get_candidate(connection, principal.tenant_id, UUID(str(value)))
                for value in ids
            ]

    async def execute_release_validation(self, *, candidate_id: UUID, trace_id: str) -> JsonDict:
        now = datetime.now(UTC)
        async with self._database.engine.begin() as connection:
            candidate = (
                (
                    await connection.execute(
                        text("SELECT * FROM release_candidates WHERE id=:id FOR UPDATE"),
                        {"id": candidate_id},
                    )
                )
                .mappings()
                .first()
            )
            if candidate is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "ReleaseCandidate unavailable",
                    "The ReleaseCandidate is unavailable.",
                )
            if candidate["status"] in {"PENDING_APPROVAL", "APPROVED", "PUBLISHING", "PUBLISHED"}:
                return _json_value(candidate["gate_summary"])
            await connection.execute(
                text(
                    "UPDATE release_candidates SET status='VALIDATING',updated_at=:now WHERE id=:id"
                ),
                {"now": now, "id": candidate_id},
            )
            findings = await self._lint_candidate(connection, candidate)
            evaluation = await self._evaluate(
                connection,
                tenant_id=UUID(str(candidate["tenant_id"])),
                space_id=UUID(str(candidate["space_id"])),
                suite_id=UUID(str(candidate["evaluation_suite_id"])),
                target_type="RELEASE_CANDIDATE",
                target_id=candidate_id,
                strategy="HYBRID",
                config={"source": "release-gate"},
                actor_id=UUID(str(candidate["created_by"])),
            )
            unresolved = int(
                (
                    await connection.execute(
                        text(
                            "SELECT count(*) FROM conflict_cases WHERE space_id=:space AND blocking=true AND status IN ('OPEN','UNRESOLVED')"
                        ),
                        {"space": candidate["space_id"]},
                    )
                ).scalar_one()
            )
            total = sum(len(values) for values in dict(candidate["manifest"])["objects"].values())
            blocking = sum(1 for item in findings if item["blocking"])
            gate = ReleaseGate(
                100 if total else 0,
                100 if not any(item["code"] == "SCHEMA_MISMATCH" for item in findings) else 0,
                blocking,
                unresolved,
                bool(evaluation["gate_passed"]),
            )
            summary = {
                "traceability_percent": gate.traceability_percent,
                "schema_compliance_percent": gate.schema_compliance_percent,
                "blocking_lint_count": gate.blocking_lint_count,
                "unresolved_blocking_conflicts": gate.unresolved_blocking_conflicts,
                "evaluation_passed": gate.evaluation_passed,
                "evaluation_run_id": evaluation["id"],
            }
            try:
                validate_release_gate(gate)
                status = "PENDING_APPROVAL"
            except ReleaseRuleViolation as exc:
                status = "FAILED"
                summary["error_code"] = exc.code
            await connection.execute(
                text(
                    "UPDATE release_candidates SET status=:status,gate_summary=CAST(:summary AS jsonb),updated_at=:now WHERE id=:id"
                ),
                {"status": status, "summary": json.dumps(summary), "now": now, "id": candidate_id},
            )
            return _json_value(summary)

    async def _lint_candidate(
        self, connection: AsyncConnection, candidate: Any
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        manifest = dict(candidate["manifest"])
        schema_id = str(candidate["schema_version_id"])
        for claim_id in manifest["objects"]["claim"]:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT cc.schema_version_id FROM claims c JOIN claim_candidates cc ON cc.id=c.candidate_id WHERE c.id=:id"
                        ),
                        {"id": UUID(claim_id)},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or str(row["schema_version_id"]) != schema_id:
                findings.append(
                    {
                        "code": "SCHEMA_MISMATCH",
                        "severity": "BLOCKING",
                        "blocking": True,
                        "object_type": "CLAIM",
                        "object_id": claim_id,
                        "message": "Claim does not match the fixed SchemaVersion.",
                        "details": {},
                    }
                )
        for relation_id in manifest["objects"]["relation"]:
            row = (
                (
                    await connection.execute(
                        text("SELECT schema_version_id FROM relations WHERE id=:id"),
                        {"id": UUID(relation_id)},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or str(row["schema_version_id"]) != schema_id:
                findings.append(
                    {
                        "code": "SCHEMA_MISMATCH",
                        "severity": "BLOCKING",
                        "blocking": True,
                        "object_type": "RELATION",
                        "object_id": relation_id,
                        "message": "Relation does not match the fixed SchemaVersion.",
                        "details": {},
                    }
                )
        for page_id in manifest["objects"]["wiki_page_version"]:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT wp.schema_version_id,wv.status FROM wiki_page_versions wv JOIN wiki_pages wp ON wp.id=wv.wiki_page_id WHERE wv.id=:id"
                        ),
                        {"id": UUID(page_id)},
                    )
                )
                .mappings()
                .first()
            )
            if (
                row is None
                or str(row["schema_version_id"]) != schema_id
                or row["status"] != "APPROVED"
            ):
                findings.append(
                    {
                        "code": "PAGE_NOT_APPROVED",
                        "severity": "BLOCKING",
                        "blocking": True,
                        "object_type": "WIKI_PAGE_VERSION",
                        "object_id": page_id,
                        "message": "Wiki page version is not approved under the fixed SchemaVersion.",
                        "details": {},
                    }
                )
        if not manifest.get("source_refs"):
            findings.append(
                {
                    "code": "SOURCE_TRACE_MISSING",
                    "severity": "BLOCKING",
                    "blocking": True,
                    "object_type": "RELEASE_CANDIDATE",
                    "object_id": str(candidate["id"]),
                    "message": "ReleaseCandidate has no fixed Source/Evidence references.",
                    "details": {},
                }
            )
        for finding in findings:
            await connection.execute(
                text(
                    "INSERT INTO release_lint_findings (id,tenant_id,space_id,candidate_id,code,severity,blocking,object_type,object_id,message,details) VALUES (:id,:tenant,:space,:candidate,:code,:severity,:blocking,:type,:object,:message,CAST(:details AS jsonb)) ON CONFLICT (candidate_id,code,object_type,object_id) DO NOTHING"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "candidate": candidate["id"],
                    "code": finding["code"],
                    "severity": finding["severity"],
                    "blocking": finding["blocking"],
                    "type": finding["object_type"],
                    "object": UUID(finding["object_id"]) if finding["object_id"] else None,
                    "message": finding["message"],
                    "details": json.dumps(finding["details"]),
                },
            )
        return findings

    async def _evaluate(
        self,
        connection: AsyncConnection,
        *,
        tenant_id: UUID,
        space_id: UUID,
        suite_id: UUID,
        target_type: str,
        target_id: UUID,
        strategy: str,
        config: dict[str, Any],
        actor_id: UUID,
        run_id: UUID | None = None,
    ) -> JsonDict:
        suite = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM evaluation_suites WHERE tenant_id=:tenant AND space_id=:space AND id=:id"
                    ),
                    {"tenant": tenant_id, "space": space_id, "id": suite_id},
                )
            )
            .mappings()
            .first()
        )
        if suite is None or suite["status"] != "ACTIVE":
            raise ApiProblem(
                409,
                "EVALUATION_SUITE_NOT_ACTIVE",
                "Evaluation suite unavailable",
                "An active EvaluationSuite is required.",
            )
        evaluation_id, now = run_id or new_uuid7(), datetime.now(UTC)
        existing = (
            await connection.execute(
                text("SELECT id FROM evaluation_runs WHERE id=:id"), {"id": evaluation_id}
            )
        ).scalar_one_or_none()
        if existing is None:
            await connection.execute(
                text(
                    "INSERT INTO evaluation_runs (id,tenant_id,space_id,suite_id,suite_version,target_type,target_id,retrieval_strategy,retrieval_config,status,started_at,created_at,created_by) VALUES (:id,:tenant,:space,:suite,:version,:type,:target,:strategy,CAST(:config AS jsonb),'RUNNING',:now,:now,:actor)"
                ),
                {
                    "id": evaluation_id,
                    "tenant": tenant_id,
                    "space": space_id,
                    "suite": suite_id,
                    "version": suite["version"],
                    "type": target_type,
                    "target": target_id,
                    "strategy": strategy,
                    "config": json.dumps(config),
                    "now": now,
                    "actor": actor_id,
                },
            )
        else:
            await connection.execute(
                text(
                    "UPDATE evaluation_runs SET status='RUNNING',started_at=COALESCE(started_at,:now) WHERE id=:id"
                ),
                {"now": now, "id": evaluation_id},
            )
        claim_ids = await self._target_claim_ids(connection, target_type, target_id)
        statements: dict[str, str] = {}
        if claim_ids:
            statement = text("SELECT id,statement FROM claims WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            statements = {
                str(row["id"]): str(row["statement"])
                for row in (await connection.execute(statement, {"ids": claim_ids}))
                .mappings()
                .all()
            }
        corpus = "\n".join(statements.values()).casefold()
        cases = (
            (
                await connection.execute(
                    text("SELECT * FROM evaluation_cases WHERE suite_id=:suite ORDER BY case_key"),
                    {"suite": suite_id},
                )
            )
            .mappings()
            .all()
        )
        passed_count = 0
        for case in cases:
            expected = {str(value) for value in case["expected_claim_ids"]}
            matched = sorted(expected.intersection(statements))
            refusal_type = (
                case["case_type"] in {"UNANSWERABLE", "INSUFFICIENT_EVIDENCE", "COUNTERFACTUAL"}
                or case["expect_refusal"]
            )
            if refusal_type:
                passed = not expected or not matched
                answer_status = "REFUSED" if passed else "COMPLETED"
            else:
                terms_ok = all(str(term).casefold() in corpus for term in case["expected_terms"])
                passed = expected.issubset(statements) and terms_ok
                answer_status = "COMPLETED" if passed else "REFUSED"
            passed_count += int(passed)
            await connection.execute(
                text(
                    "INSERT INTO evaluation_results (id,run_id,case_id,case_key,case_type,passed,answer_status,matched_claim_ids,error_code,details) VALUES (:id,:run,:case,:key,:type,:passed,:status,:matched,:error,CAST(:details AS jsonb)) ON CONFLICT (run_id,case_id) DO NOTHING"
                ),
                {
                    "id": new_uuid7(),
                    "run": evaluation_id,
                    "case": case["id"],
                    "key": case["case_key"],
                    "type": case["case_type"],
                    "passed": passed,
                    "status": answer_status,
                    "matched": [UUID(value) for value in matched],
                    "error": None if passed else "EVALUATION_EXPECTATION_MISSED",
                    "details": json.dumps(
                        {
                            "expected_claim_ids": sorted(expected),
                            "expected_terms": list(case["expected_terms"]),
                        }
                    ),
                },
            )
        rate = int(passed_count * 100 / len(cases)) if cases else 0
        gate_passed = rate >= int(suite["minimum_pass_rate"])
        metrics = {
            "cases": len(cases),
            "passed": passed_count,
            "failed": len(cases) - passed_count,
            "pass_rate": rate,
            "minimum_pass_rate": suite["minimum_pass_rate"],
        }
        await connection.execute(
            text(
                "UPDATE evaluation_runs SET status='SUCCEEDED',metrics=CAST(:metrics AS jsonb),gate_passed=:gate,completed_at=:now WHERE id=:id"
            ),
            {"metrics": json.dumps(metrics), "gate": gate_passed, "now": now, "id": evaluation_id},
        )
        event_principal = Principal(
            actor_type=self._system_actor_type(),
            actor_id=actor_id,
            tenant_id=tenant_id,
            subject="quality-workflow",
            audience=("nexweave-api",),
            tenant_roles=frozenset(),
            clearance=self._internal_classification(),
            token_id=f"evaluation:{evaluation_id}",
        )
        await self._insert_outbox(
            connection,
            principal=event_principal,
            event_type="io.nexweave.evaluation.completed.v1",
            aggregate_type="EvaluationRun",
            aggregate_id=evaluation_id,
            aggregate_version=1,
            space_id=space_id,
            trace_id="",
            payload={
                "evaluation_run_id": str(evaluation_id),
                "target_type": target_type,
                "target_id": str(target_id),
                "suite_id": str(suite_id),
                "gate_passed": gate_passed,
                "metrics": metrics,
            },
        )
        return {"id": str(evaluation_id), "gate_passed": gate_passed, "metrics": metrics}

    async def _target_claim_ids(
        self, connection: AsyncConnection, target_type: str, target_id: UUID
    ) -> list[UUID]:
        if target_type == "RELEASE_CANDIDATE":
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT object_id FROM release_candidate_items WHERE candidate_id=:id AND object_type='CLAIM'"
                        ),
                        {"id": target_id},
                    )
                )
                .scalars()
                .all()
            )
        else:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT object_id FROM release_items WHERE release_id=:id AND object_type='CLAIM'"
                        ),
                        {"id": target_id},
                    )
                )
                .scalars()
                .all()
            )
        return [UUID(str(value)) for value in rows]

    async def create_evaluation_run(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        workflow_task_id: UUID,
        workflow_id: str,
        trace_id: str,
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            existing = (
                await connection.execute(
                    text(
                        "SELECT id FROM evaluation_runs WHERE tenant_id=:tenant AND workflow_task_id=:task"
                    ),
                    {"tenant": principal.tenant_id, "task": workflow_task_id},
                )
            ).scalar_one_or_none()
        if existing is not None:
            return await self.get_evaluation_run(principal=principal, run_id=UUID(str(existing)))
        run_id, now = new_uuid7(), datetime.now(UTC)
        suite = await self.get_evaluation_suite(
            principal=principal, suite_id=UUID(str(payload["suite_id"]))
        )
        if suite["space_id"] != str(space_id):
            raise ApiProblem(
                409,
                "EVALUATION_SCOPE_CONFLICT",
                "Evaluation scope conflict",
                "Suite and target must share a space.",
            )
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO evaluation_runs (id,tenant_id,space_id,suite_id,suite_version,target_type,target_id,workflow_task_id,workflow_id,retrieval_strategy,retrieval_config,status,created_at,created_by) VALUES (:id,:tenant,:space,:suite,:version,:type,:target,:task,:workflow,:strategy,CAST(:config AS jsonb),'CREATED',:now,:actor)"
                ),
                {
                    "id": run_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "suite": payload["suite_id"],
                    "version": suite["version"],
                    "type": payload["target_type"],
                    "target": payload["target_id"],
                    "task": workflow_task_id,
                    "workflow": workflow_id,
                    "strategy": payload["retrieval_strategy"],
                    "config": json.dumps(payload.get("retrieval_config", {})),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="quality.run.create",
                resource_type="EvaluationRun",
                resource_id=run_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "target_type": payload["target_type"],
                    "target_id": str(payload["target_id"]),
                },
            )
        return await self.get_evaluation_run(principal=principal, run_id=run_id)

    async def execute_evaluation_run(self, *, run_id: UUID) -> JsonDict:
        async with self._database.engine.begin() as connection:
            run = (
                (
                    await connection.execute(
                        text("SELECT * FROM evaluation_runs WHERE id=:id FOR UPDATE"),
                        {"id": run_id},
                    )
                )
                .mappings()
                .first()
            )
            if run is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "EvaluationRun unavailable",
                    "The EvaluationRun is unavailable.",
                )
            if run["status"] == "SUCCEEDED":
                return _json_value(run["metrics"])
            return await self._evaluate(
                connection,
                tenant_id=UUID(str(run["tenant_id"])),
                space_id=UUID(str(run["space_id"])),
                suite_id=UUID(str(run["suite_id"])),
                target_type=str(run["target_type"]),
                target_id=UUID(str(run["target_id"])),
                strategy=str(run["retrieval_strategy"]),
                config=dict(run["retrieval_config"]),
                actor_id=UUID(str(run["created_by"])),
                run_id=run_id,
            )

    async def get_evaluation_run(self, *, principal: Principal, run_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM evaluation_runs WHERE tenant_id=:tenant AND id=:id"),
                        {"tenant": principal.tenant_id, "id": run_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "EvaluationRun unavailable",
                    "The EvaluationRun is unavailable.",
                )
            results = (
                (
                    await connection.execute(
                        text(
                            "SELECT case_key,case_type,passed,answer_status,matched_claim_ids,error_code,details FROM evaluation_results WHERE run_id=:id ORDER BY case_key"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
        return _json_value({**row, "results": [dict(item) for item in results]})

    async def record_release_approval(
        self,
        *,
        principal: Principal,
        candidate_id: UUID,
        decision: str,
        reason: str,
        channel: str,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            candidate = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM release_candidates WHERE tenant_id=:tenant AND id=:id FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": candidate_id},
                    )
                )
                .mappings()
                .first()
            )
            if candidate is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "ReleaseCandidate unavailable",
                    "The ReleaseCandidate is unavailable.",
                )
            if candidate["status"] != "PENDING_APPROVAL":
                raise ApiProblem(
                    409,
                    "RELEASE_NOT_READY",
                    "ReleaseCandidate is not ready",
                    "Quality validation must pass before approval.",
                )
            try:
                validate_release_approver(
                    creator_id=UUID(str(candidate["created_by"])), approver_id=principal.actor_id
                )
            except ReleaseRuleViolation as exc:
                raise ApiProblem(409, exc.code, "Release approval rejected", str(exc)) from exc
            await connection.execute(
                text(
                    "INSERT INTO release_approvals (id,candidate_id,decision,reason,channel,created_at,created_by) VALUES (:id,:candidate,:decision,:reason,:channel,:now,:actor)"
                ),
                {
                    "id": new_uuid7(),
                    "candidate": candidate_id,
                    "decision": decision,
                    "reason": reason,
                    "channel": channel,
                    "now": datetime.now(UTC),
                    "actor": principal.actor_id,
                },
            )
            status = "APPROVED" if decision == "APPROVED" else "REJECTED"
            await connection.execute(
                text(
                    "UPDATE release_candidates SET status=:status,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "status": status,
                    "now": datetime.now(UTC),
                    "actor": principal.actor_id,
                    "id": candidate_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.approve" if decision == "APPROVED" else "release.reject",
                resource_type="ReleaseCandidate",
                resource_id=candidate_id,
                space_id=UUID(str(candidate["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"channel": channel},
            )
            return _json_value({**candidate, "status": status})

        return await self._idempotent(
            principal=principal,
            operation=f"release.approval:{candidate_id}",
            key=idempotency_key,
            request={"decision": decision, "reason": reason, "channel": channel},
            mutation=mutation,
        )

    async def publish_release(
        self, *, candidate_id: UUID, approver_id: UUID, channel: str, reason: str, trace_id: str
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            candidate = (
                (
                    await connection.execute(
                        text("SELECT * FROM release_candidates WHERE id=:id"), {"id": candidate_id}
                    )
                )
                .mappings()
                .first()
            )
            if candidate is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "ReleaseCandidate unavailable",
                    "The ReleaseCandidate is unavailable.",
                )
            documents = await self._projection_documents(connection, candidate)
        vectors = (
            await self._model_gateway.embedding(
                model_profile_id=str(candidate["model_profile_id"]),
                texts=tuple(item["body"] for item in documents),
            )
            if documents
            else ()
        )
        now, release_id = datetime.now(UTC), new_uuid7()
        principal = Principal(
            actor_type=self._system_actor_type(),
            actor_id=approver_id,
            tenant_id=UUID(str(candidate["tenant_id"])),
            subject="release-workflow",
            audience=("nexweave-api",),
            tenant_roles=frozenset(),
            clearance=self._internal_classification(),
            token_id=f"workflow:{candidate_id}",
        )
        async with self._database.engine.begin() as connection:
            candidate = (
                (
                    await connection.execute(
                        text("SELECT * FROM release_candidates WHERE id=:id FOR UPDATE"),
                        {"id": candidate_id},
                    )
                )
                .mappings()
                .one()
            )
            existing = (
                (
                    await connection.execute(
                        text("SELECT * FROM releases WHERE candidate_id=:id"), {"id": candidate_id}
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                return _json_value(existing)
            approval = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM release_approvals WHERE candidate_id=:id AND decision='APPROVED' AND created_by=:actor ORDER BY created_at DESC LIMIT 1"
                        ),
                        {"id": candidate_id, "actor": approver_id},
                    )
                )
                .mappings()
                .first()
            )
            if candidate["status"] != "APPROVED" or approval is None:
                raise ApiProblem(
                    409,
                    "RELEASE_APPROVAL_REQUIRED",
                    "Release approval required",
                    "A matching audited Publisher approval is required.",
                )
            await connection.execute(
                text(
                    "UPDATE release_candidates SET status='PUBLISHING',updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"now": now, "actor": approver_id, "id": candidate_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO releases (id,tenant_id,space_id,candidate_id,version,status,manifest,manifest_checksum,schema_version_id,composition_checksum,prompt_version_id,model_profile_id,index_config,published_at,published_by) VALUES (:id,:tenant,:space,:candidate,:version,'PUBLISHED',CAST(:manifest AS jsonb),:checksum,:schema,:composition,:prompt,:model,CAST(:index AS jsonb),:now,:actor)"
                ),
                {
                    "id": release_id,
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "candidate": candidate_id,
                    "version": candidate["version"],
                    "manifest": json.dumps(dict(candidate["manifest"])),
                    "checksum": candidate["manifest_checksum"],
                    "schema": candidate["schema_version_id"],
                    "composition": candidate["composition_checksum"],
                    "prompt": candidate["prompt_version_id"],
                    "model": candidate["model_profile_id"],
                    "index": json.dumps(dict(candidate["index_config"])),
                    "now": now,
                    "actor": approver_id,
                },
            )
            await self._persist_release_items(connection, release_id, candidate)
            await self._persist_projection(connection, release_id, candidate, documents, vectors)
            await self._move_pointer(
                connection,
                principal=principal,
                space_id=UUID(str(candidate["space_id"])),
                release_id=release_id,
                channel=channel,
                reason=reason,
                expected_version=None,
                trace_id=trace_id,
            )
            await connection.execute(
                text(
                    "UPDATE release_candidates SET status='PUBLISHED',updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"now": now, "actor": approver_id, "id": candidate_id},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.release.published.v1",
                aggregate_type="Release",
                aggregate_id=release_id,
                aggregate_version=1,
                space_id=UUID(str(candidate["space_id"])),
                trace_id=trace_id,
                payload={
                    "release_id": str(release_id),
                    "space_id": str(candidate["space_id"]),
                    "version": candidate["version"],
                    "manifest_checksum": candidate["manifest_checksum"],
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.publish",
                resource_type="Release",
                resource_id=release_id,
                space_id=UUID(str(candidate["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"candidate_id": str(candidate_id), "channel": channel},
            )
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM releases WHERE id=:id"), {"id": release_id}
                    )
                )
                .mappings()
                .one()
            )
        return _json_value(row)

    async def publish_approved_release(
        self, *, candidate_id: UUID, approver_id: UUID, trace_id: str
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            approval = (
                (
                    await connection.execute(
                        text(
                            "SELECT channel,reason FROM release_approvals WHERE candidate_id=:candidate "
                            "AND decision='APPROVED' AND created_by=:actor ORDER BY created_at DESC LIMIT 1"
                        ),
                        {"candidate": candidate_id, "actor": approver_id},
                    )
                )
                .mappings()
                .first()
            )
        if approval is None:
            raise ApiProblem(
                409,
                "RELEASE_APPROVAL_REQUIRED",
                "Release approval required",
                "The Workflow cannot publish without the matching audited approval.",
            )
        return await self.publish_release(
            candidate_id=candidate_id,
            approver_id=approver_id,
            channel=str(approval["channel"]),
            reason=str(approval["reason"]),
            trace_id=trace_id,
        )

    @staticmethod
    def _system_actor_type() -> Any:
        from nexweave_domain import ActorType

        return ActorType.USER

    @staticmethod
    def _internal_classification() -> Any:
        from nexweave_domain import DataClassification

        return DataClassification.INTERNAL

    async def _persist_release_items(
        self, connection: AsyncConnection, release_id: UUID, candidate: Any
    ) -> None:
        manifest = dict(candidate["manifest"])
        refs: list[tuple[str, str]] = []
        refs.extend(
            (key.upper(), value) for key, values in manifest["objects"].items() for value in values
        )
        refs.extend(("EVIDENCE", value) for value in manifest["evidence_ids"])
        refs.extend(("ENTITY", value) for value in manifest["entity_ids"])
        for object_type, value in refs:
            snapshot = await self._object_snapshot(connection, object_type, UUID(value))
            await connection.execute(
                text(
                    "INSERT INTO release_items (id,tenant_id,space_id,release_id,object_type,object_id,object_checksum,snapshot) VALUES (:id,:tenant,:space,:release,:type,:object,:checksum,CAST(:snapshot AS jsonb))"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "release": release_id,
                    "type": object_type,
                    "object": UUID(value),
                    "checksum": snapshot.get("content_checksum") or snapshot.get("excerpt_hash"),
                    "snapshot": json.dumps(snapshot),
                },
            )

    async def _object_snapshot(
        self, connection: AsyncConnection, object_type: str, object_id: UUID
    ) -> JsonDict:
        table = {
            "CLAIM": "claims",
            "RELATION": "relations",
            "EVIDENCE": "evidence_records",
            "ENTITY": "knowledge_entities",
            "WIKI_PAGE_VERSION": "wiki_page_versions",
        }[object_type]
        row = (
            (
                await connection.execute(
                    text(f"SELECT * FROM {table} WHERE id=:id"), {"id": object_id}
                )
            )
            .mappings()
            .one()
        )  # noqa: S608
        return _json_value(row)

    async def _projection_documents(
        self, connection: AsyncConnection, candidate: Any
    ) -> list[dict[str, Any]]:
        manifest = dict(candidate["manifest"])
        docs: list[dict[str, Any]] = []
        for value in manifest["objects"]["claim"]:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT c.id,c.statement,c.predicate_key,c.object_value,e.display_name,CASE max(CASE sv.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1 WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END) WHEN 0 THEN 'PUBLIC' WHEN 1 THEN 'INTERNAL' WHEN 2 THEN 'CONFIDENTIAL' ELSE 'HIGHLY_RESTRICTED' END AS classification FROM claims c JOIN knowledge_entities e ON e.id=c.subject_entity_id JOIN evidence_records er ON er.claim_id=c.id JOIN source_anchors sa ON sa.id=er.source_anchor_id JOIN source_versions sv ON sv.id=sa.source_version_id WHERE c.id=:id GROUP BY c.id,e.display_name"
                        ),
                        {"id": UUID(value)},
                    )
                )
                .mappings()
                .one()
            )
            docs.append(
                {
                    "object_type": "CLAIM",
                    "object_id": str(row["id"]),
                    "title": str(row["display_name"]),
                    "body": str(row["statement"]),
                    "attributes": {
                        "predicate_key": row["predicate_key"],
                        "object_value": row["object_value"],
                    },
                    "classification": row["classification"],
                }
            )
        for value in manifest["objects"]["wiki_page_version"]:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT wv.id,wv.markdown,wp.title,ks.default_classification AS classification FROM wiki_page_versions wv JOIN wiki_pages wp ON wp.id=wv.wiki_page_id JOIN knowledge_spaces ks ON ks.id=wv.space_id WHERE wv.id=:id"
                        ),
                        {"id": UUID(value)},
                    )
                )
                .mappings()
                .one()
            )
            docs.append(
                {
                    "object_type": "WIKI_PAGE_VERSION",
                    "object_id": str(row["id"]),
                    "title": str(row["title"]),
                    "body": str(row["markdown"]),
                    "attributes": {},
                    "classification": row["classification"],
                }
            )
        return docs

    async def _persist_projection(
        self,
        connection: AsyncConnection,
        release_id: UUID,
        candidate: Any,
        documents: list[dict[str, Any]],
        vectors: Any,
    ) -> None:
        for item, vector in zip(documents, vectors, strict=True):
            vector_value = "[" + ",".join(f"{float(value):.9f}" for value in vector) + "]"
            await connection.execute(
                text(
                    "INSERT INTO release_search_documents (id,tenant_id,space_id,release_id,object_type,object_id,title,body,attributes,classification,search_vector,embedding,projection_version) VALUES (:id,:tenant,:space,:release,:type,:object,:title,:body,CAST(:attributes AS jsonb),:classification,to_tsvector('simple',:document),CAST(:embedding AS vector),'m7-r1')"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": candidate["tenant_id"],
                    "space": candidate["space_id"],
                    "release": release_id,
                    "type": item["object_type"],
                    "object": UUID(item["object_id"]),
                    "title": item["title"],
                    "body": item["body"],
                    "attributes": json.dumps(item["attributes"]),
                    "classification": item["classification"],
                    "document": f"{item['title']} {item['body']}",
                    "embedding": vector_value,
                },
            )

    async def _move_pointer(
        self,
        connection: AsyncConnection,
        *,
        principal: Principal,
        space_id: UUID,
        release_id: UUID,
        channel: str,
        reason: str,
        expected_version: int | None,
        trace_id: str,
    ) -> JsonDict:
        pointer = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM release_pointers WHERE tenant_id=:tenant AND space_id=:space AND channel=:channel FOR UPDATE"
                    ),
                    {"tenant": principal.tenant_id, "space": space_id, "channel": channel},
                )
            )
            .mappings()
            .first()
        )
        if pointer is None:
            if expected_version not in (None, 0):
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Release pointer changed",
                    "Reload the channel pointer and retry.",
                )
            pointer_id, version, old_release = new_uuid7(), 1, None
            await connection.execute(
                text(
                    "INSERT INTO release_pointers (id,tenant_id,space_id,channel,release_id,version,updated_at,updated_by) VALUES (:id,:tenant,:space,:channel,:release,1,:now,:actor)"
                ),
                {
                    "id": pointer_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "channel": channel,
                    "release": release_id,
                    "now": datetime.now(UTC),
                    "actor": principal.actor_id,
                },
            )
        else:
            if expected_version is not None and int(pointer["version"]) != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Release pointer changed",
                    "Reload the channel pointer and retry.",
                )
            pointer_id, version, old_release = (
                UUID(str(pointer["id"])),
                int(pointer["version"]) + 1,
                pointer["release_id"],
            )
            await connection.execute(
                text(
                    "UPDATE release_pointers SET release_id=:release,version=:version,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "release": release_id,
                    "version": version,
                    "now": datetime.now(UTC),
                    "actor": principal.actor_id,
                    "id": pointer_id,
                },
            )
        await connection.execute(
            text(
                "INSERT INTO release_pointer_history (id,tenant_id,space_id,pointer_id,channel,old_release_id,new_release_id,reason,pointer_version,created_at,created_by) VALUES (:id,:tenant,:space,:pointer,:channel,:old,:new,:reason,:version,:now,:actor)"
            ),
            {
                "id": new_uuid7(),
                "tenant": principal.tenant_id,
                "space": space_id,
                "pointer": pointer_id,
                "channel": channel,
                "old": old_release,
                "new": release_id,
                "reason": reason,
                "version": version,
                "now": datetime.now(UTC),
                "actor": principal.actor_id,
            },
        )
        await self._insert_outbox(
            connection,
            principal=principal,
            event_type="io.nexweave.release.pointer-changed.v1",
            aggregate_type="ReleasePointer",
            aggregate_id=pointer_id,
            aggregate_version=version,
            space_id=space_id,
            trace_id=trace_id,
            payload={
                "pointer_id": str(pointer_id),
                "channel": channel,
                "old_release_id": str(old_release) if old_release else None,
                "new_release_id": str(release_id),
                "reason": reason,
            },
        )
        row = (
            (
                await connection.execute(
                    text("SELECT * FROM release_pointers WHERE id=:id"), {"id": pointer_id}
                )
            )
            .mappings()
            .one()
        )
        return _json_value(row)

    async def switch_release_pointer(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        release_id: UUID,
        channel: str,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            release = (
                await connection.execute(
                    text(
                        "SELECT id FROM releases WHERE tenant_id=:tenant AND space_id=:space AND id=:id"
                    ),
                    {"tenant": principal.tenant_id, "space": space_id, "id": release_id},
                )
            ).scalar_one_or_none()
            if release is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Release unavailable",
                    "The target Release is unavailable.",
                )
            result = await self._move_pointer(
                connection,
                principal=principal,
                space_id=space_id,
                release_id=release_id,
                channel=channel,
                reason=reason,
                expected_version=expected_version,
                trace_id=trace_id,
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.pointer.switch",
                resource_type="ReleasePointer",
                resource_id=UUID(str(result["id"])),
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "release_id": str(release_id),
                    "channel": channel,
                    "version": result["version"],
                },
            )
            return result

        return await self._idempotent(
            principal=principal,
            operation=f"release.pointer.switch:{space_id}:{channel}",
            key=idempotency_key,
            request={
                "release_id": str(release_id),
                "reason": reason,
                "expected_version": expected_version,
            },
            mutation=mutation,
        )

    async def get_release_pointer(
        self, *, principal: Principal, space_id: UUID, channel: str
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM release_pointers WHERE tenant_id=:tenant AND space_id=:space AND channel=:channel"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id, "channel": channel},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Release pointer unavailable",
                "The requested channel has no Release pointer.",
            )
        return _json_value(row)

    async def list_releases(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT r.*,d.created_at AS deprecated_at,d.reason AS deprecation_reason FROM releases r LEFT JOIN release_deprecations d ON d.release_id=r.id WHERE r.tenant_id=:tenant AND r.space_id=:space ORDER BY r.published_at DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def get_release(self, *, principal: Principal, release_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT r.*,d.created_at AS deprecated_at,d.reason AS deprecation_reason FROM releases r LEFT JOIN release_deprecations d ON d.release_id=r.id WHERE r.tenant_id=:tenant AND r.id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": release_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Release unavailable", "The Release is unavailable."
            )
        return _json_value(row)

    async def export_release(self, *, principal: Principal, release_id: UUID) -> JsonDict:
        release = await self.get_release(principal=principal, release_id=release_id)
        async with self._database.engine.connect() as connection:
            items = (
                (
                    await connection.execute(
                        text(
                            "SELECT object_type,object_id,object_checksum,snapshot FROM release_items WHERE release_id=:release ORDER BY object_type,object_id"
                        ),
                        {"release": release_id},
                    )
                )
                .mappings()
                .all()
            )
        return {"release": release, "items": [_json_value(item) for item in items]}

    async def rebuild_release_projection(
        self, *, principal: Principal, release_id: UUID, idempotency_key: str, trace_id: str
    ) -> JsonDict:
        release = await self.get_release(principal=principal, release_id=release_id)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            candidate = (
                (
                    await connection.execute(
                        text("SELECT * FROM release_candidates WHERE id=:id FOR SHARE"),
                        {"id": UUID(str(release["candidate_id"]))},
                    )
                )
                .mappings()
                .one()
            )
            documents = await self._projection_documents(connection, candidate)
            vectors = (
                await self._model_gateway.embedding(
                    model_profile_id=str(candidate["model_profile_id"]),
                    texts=tuple(f"{item['title']}\n{item['body']}" for item in documents),
                )
                if documents
                else ()
            )
            await connection.execute(
                text("DELETE FROM release_search_documents WHERE release_id=:release"),
                {"release": release_id},
            )
            await self._persist_projection(connection, release_id, candidate, documents, vectors)
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.projection.rebuild",
                resource_type="Release",
                resource_id=release_id,
                space_id=UUID(str(release["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"document_count": len(documents), "projection_version": "m7-r1"},
            )
            return {
                "release_id": str(release_id),
                "projection_version": "m7-r1",
                "document_count": len(documents),
                "rebuilt": True,
            }

        return await self._idempotent(
            principal=principal,
            operation=f"release.projection.rebuild:{release_id}",
            key=idempotency_key,
            request={"release_id": str(release_id), "projection_version": "m7-r1"},
            mutation=mutation,
        )

    async def deprecate_release(
        self,
        *,
        principal: Principal,
        release_id: UUID,
        reason: str,
        replacement_release_id: UUID | None,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        release = await self.get_release(principal=principal, release_id=release_id)
        deprecated_at = datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            await connection.execute(
                text(
                    "INSERT INTO release_deprecations (id,tenant_id,space_id,release_id,reason,replacement_release_id,created_at,created_by) VALUES (:id,:tenant,:space,:release,:reason,:replacement,:now,:actor)"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": UUID(str(release["space_id"])),
                    "release": release_id,
                    "reason": reason,
                    "replacement": replacement_release_id,
                    "now": deprecated_at,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.release.deprecated.v1",
                aggregate_type="Release",
                aggregate_id=release_id,
                aggregate_version=1,
                space_id=UUID(str(release["space_id"])),
                trace_id=trace_id,
                payload={
                    "release_id": str(release_id),
                    "reason": reason,
                    "replacement_release_id": str(replacement_release_id)
                    if replacement_release_id
                    else None,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="release.deprecate",
                resource_type="Release",
                resource_id=release_id,
                space_id=UUID(str(release["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "replacement_release_id": str(replacement_release_id)
                    if replacement_release_id
                    else None
                },
            )
            return {
                **release,
                "deprecated_at": deprecated_at.isoformat(),
                "deprecation_reason": reason,
            }

        return await self._idempotent(
            principal=principal,
            operation=f"release.deprecate:{release_id}",
            key=idempotency_key,
            request={
                "reason": reason,
                "replacement_release_id": str(replacement_release_id)
                if replacement_release_id
                else None,
            },
            mutation=mutation,
        )

    async def query_release(
        self, *, principal: Principal, release_id: UUID, payload: dict[str, Any], trace_id: str
    ) -> JsonDict:
        release = await self.get_release(principal=principal, release_id=release_id)
        async with self._database.engine.connect() as connection:
            existing = (
                await connection.execute(
                    text(
                        "SELECT qa.id FROM query_sessions qs JOIN query_answers qa ON qa.query_session_id=qs.id WHERE qs.tenant_id=:tenant AND qs.created_by=:actor AND qs.client_request_id=:client"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "actor": principal.actor_id,
                        "client": payload["client_request_id"],
                    },
                )
            ).scalar_one_or_none()
        if existing is not None:
            previous = await self.get_query_answer(
                principal=principal, answer_id=UUID(str(existing))
            )
            config = previous["retrieval_config"]
            if (
                str(previous["release_id"]) != str(release_id)
                or previous["question"] != payload["question"]
                or previous["retrieval_strategy"] != payload["strategy"]
                or config.get("top_k") != payload["top_k"]
                or config.get("filters", {}) != payload.get("filters", {})
            ):
                raise ApiProblem(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Query request changed",
                    "Use a new client request ID for different query inputs.",
                )
            return previous
        query_vector = (
            await self._model_gateway.embedding(
                model_profile_id=str(release["model_profile_id"]), texts=(payload["question"],)
            )
        )[0]
        vector_value = "[" + ",".join(f"{float(value):.9f}" for value in query_vector) + "]"
        clearance = CLASSIFICATION_LEVEL[principal.clearance.value]
        async with self._database.engine.connect() as connection:
            base = "release_id=:release AND CASE classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1 WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END <= :clearance"
            keyword = (
                (
                    await connection.execute(
                        text(
                            f"SELECT object_id,ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector,plainto_tsquery('simple',:query)) DESC,object_id) AS rank FROM release_search_documents WHERE {base} AND search_vector @@ plainto_tsquery('simple',:query) ORDER BY rank LIMIT :limit"
                        ),
                        {
                            "release": release_id,
                            "clearance": clearance,
                            "query": payload["question"],
                            "limit": payload["top_k"] * 4,
                        },
                    )
                )
                .mappings()
                .all()
            )
            semantic = (
                (
                    await connection.execute(
                        text(
                            f"SELECT object_id,1-(embedding <=> CAST(:embedding AS vector)) AS similarity,ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:embedding AS vector),object_id) AS rank FROM release_search_documents WHERE {base} ORDER BY embedding <=> CAST(:embedding AS vector),object_id LIMIT :limit"
                        ),
                        {
                            "release": release_id,
                            "clearance": clearance,
                            "embedding": vector_value,
                            "limit": payload["top_k"] * 4,
                        },
                    )
                )
                .mappings()
                .all()
            )
            rankings: dict[str, list[str]] = {}
            strategy = payload["strategy"]
            if strategy in {"KEYWORD", "ATTRIBUTE", "HYBRID"}:
                rankings["keyword"] = [str(item["object_id"]) for item in keyword]
            if strategy in {"SEMANTIC", "HYBRID"}:
                rankings["semantic"] = [str(item["object_id"]) for item in semantic]
            keyword_ids = {str(item["object_id"]) for item in keyword}
            semantic_similarity = {
                str(item["object_id"]): float(item["similarity"]) for item in semantic
            }
            fused = [
                item
                for item in reciprocal_rank_fusion(rankings)
                if item[0] in keyword_ids or semantic_similarity.get(item[0], -1.0) >= 0.90
            ][: payload["top_k"]]
            ids = [UUID(item[0]) for item in fused]
            rows: Sequence[Any] = []
            if ids:
                statement = text(
                    "SELECT object_type,object_id,title,body FROM release_search_documents WHERE release_id=:release AND object_id IN :ids"
                ).bindparams(bindparam("ids", expanding=True))
                rows = (
                    (await connection.execute(statement, {"release": release_id, "ids": ids}))
                    .mappings()
                    .all()
                )
            by_id = {str(row["object_id"]): row for row in rows}
            hits = [
                {
                    "object_type": by_id[item_id]["object_type"],
                    "object_id": item_id,
                    "title": by_id[item_id]["title"],
                    "text": by_id[item_id]["body"],
                    "ranks": ranks,
                    "fusion_score": score,
                }
                for item_id, score, ranks in fused
                if item_id in by_id
            ]
            citations = await self._visible_citations(connection, principal, release_id, hits)
            hits = await self._supported_hits(connection, release_id, hits, citations)
            # Draft conflict details have no fixed-release classification contract.
            conflicts: list[dict[str, Any]] = []
        answer_id, session_id, now = new_uuid7(), new_uuid7(), datetime.now(UTC)
        if citations:
            statements = [str(hit["text"]) for hit in hits if hit["object_type"] == "CLAIM"]
            status, direct = "COMPLETED", "；".join(statements[:3])
            uncertainty = "回答仅由当前固定 Release 中可见且 Anchor 有效的证据支持；RRF 分数不是事实置信度。冲突需在有权限的冲突工作台另行核查。"
        else:
            status, direct = "REFUSED", "当前固定 Release 中没有足够的可见有效证据，无法下结论。"
            uncertainty = "证据不足或访问级别不允许展示引用；冲突需在有权限的冲突工作台另行核查。"
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO query_sessions (id,tenant_id,space_id,release_id,client_request_id,policy_snapshot,status,created_at,created_by) VALUES (:id,:tenant,:space,:release,:client,CAST(:policy AS jsonb),'CLOSED',:now,:actor)"
                ),
                {
                    "id": session_id,
                    "tenant": principal.tenant_id,
                    "space": UUID(str(release["space_id"])),
                    "release": release_id,
                    "client": payload["client_request_id"],
                    "policy": json.dumps(
                        {"clearance": principal.clearance.value, "single_release": True}
                    ),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO query_answers (id,query_session_id,tenant_id,space_id,release_id,question,status,direct_answer,key_basis,uncertainty,conflicts,retrieval_strategy,retrieval_config,model_profile_id,prompt_version_id,created_at) VALUES (:id,:session,:tenant,:space,:release,:question,:status,:answer,:basis,:uncertainty,CAST(:conflicts AS jsonb),:strategy,CAST(:config AS jsonb),:model,:prompt,:now)"
                ),
                {
                    "id": answer_id,
                    "session": session_id,
                    "tenant": principal.tenant_id,
                    "space": UUID(str(release["space_id"])),
                    "release": release_id,
                    "question": payload["question"],
                    "status": status,
                    "answer": direct,
                    "basis": [str(hit["text"]) for hit in hits[:3]],
                    "uncertainty": uncertainty,
                    "conflicts": json.dumps([_json_value(item) for item in conflicts]),
                    "strategy": strategy,
                    "config": json.dumps(
                        {
                            "top_k": payload["top_k"],
                            "filters": payload.get("filters", {}),
                            "rrf_constant": 60,
                        }
                    ),
                    "model": UUID(str(release["model_profile_id"])),
                    "prompt": UUID(str(release["prompt_version_id"])),
                    "now": now,
                },
            )
            for item in citations:
                citation_id = new_uuid7()
                await connection.execute(
                    text(
                        "INSERT INTO citations (id,tenant_id,space_id,answer_id,release_id,evidence_id,source_version_id,source_anchor_id,claim_id,relation_id,excerpt,locator,status,created_at) VALUES (:id,:tenant,:space,:answer,:release,:evidence,:source,:anchor,:claim,:relation,:excerpt,CAST(:locator AS jsonb),'VALID',:now)"
                    ),
                    {
                        "id": citation_id,
                        "tenant": principal.tenant_id,
                        "space": UUID(str(release["space_id"])),
                        "answer": answer_id,
                        "release": release_id,
                        "evidence": item["evidence_id"],
                        "source": item["source_version_id"],
                        "anchor": item["source_anchor_id"],
                        "claim": item["claim_id"],
                        "relation": item["relation_id"],
                        "excerpt": item["excerpt"],
                        "locator": json.dumps(item["locator"]),
                        "now": now,
                    },
                )
                item["id"] = str(citation_id)
            await self._insert_audit(
                connection,
                principal=principal,
                action="query.release",
                resource_type="QueryAnswer",
                resource_id=answer_id,
                space_id=UUID(str(release["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "release_id": str(release_id),
                    "status": status,
                    "citation_count": len(citations),
                },
            )
        return {
            "id": str(answer_id),
            "query_session_id": str(session_id),
            "tenant_id": str(principal.tenant_id),
            "space_id": release["space_id"],
            "release_id": str(release_id),
            "question": payload["question"],
            "status": status,
            "direct_answer": direct,
            "key_basis": [str(hit["text"]) for hit in hits[:3]],
            "uncertainty": uncertainty,
            "conflicts": [_json_value(item) for item in conflicts],
            "retrieval_strategy": strategy,
            "retrieval_config": {
                "top_k": payload["top_k"],
                "filters": payload.get("filters", {}),
                "rrf_constant": 60,
            },
            "model_profile_id": release["model_profile_id"],
            "prompt_version_id": release["prompt_version_id"],
            "created_at": now.isoformat(),
            "citations": citations,
            "retrieval_hits": hits,
        }

    async def _visible_citations(
        self,
        connection: AsyncConnection,
        principal: Principal,
        release_id: UUID,
        hits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        claim_ids = [
            UUID(str(item["object_id"])) for item in hits if item["object_type"] == "CLAIM"
        ]
        if not claim_ids:
            return []
        statement = text("""
            SELECT er.id AS evidence_id,er.claim_id,er.relation_id,sa.source_version_id,
                   sa.id AS source_anchor_id,sa.locators,sv.classification,
                   sd.classification AS document_classification,rs.classification AS claim_classification,
                   (SELECT max(greatest(
                       CASE all_sv.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                           WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END,
                       CASE all_sd.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                           WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END))
                    FROM release_items all_e
                    JOIN source_anchors all_sa ON CAST(all_sa.id AS text)=all_e.snapshot->>'source_anchor_id'
                    JOIN source_versions all_sv ON all_sv.id=all_sa.source_version_id
                    JOIN source_documents all_sd ON all_sd.id=all_sv.source_document_id
                    WHERE all_e.release_id=:release AND all_e.object_type='EVIDENCE'
                        AND all_e.snapshot->>'claim_id'=CAST(er.claim_id AS text)
                   ) AS current_claim_level
            FROM evidence_records er
            JOIN source_anchors sa ON sa.id=er.source_anchor_id AND sa.status='VALID'
            JOIN source_versions sv ON sv.id=sa.source_version_id
            JOIN source_documents sd ON sd.id=sv.source_document_id AND sd.status<>'ARCHIVED'
            JOIN release_items rie ON rie.release_id=:release AND rie.object_type='EVIDENCE'
                AND rie.object_id=er.id AND rie.tenant_id=:tenant
            JOIN release_items ric ON ric.release_id=rie.release_id AND ric.object_type='CLAIM'
                AND ric.object_id=er.claim_id
            JOIN release_search_documents rs ON rs.release_id=ric.release_id
                AND rs.object_type='CLAIM' AND rs.object_id=ric.object_id
            WHERE er.status='ACCEPTED' AND er.claim_id IN :ids
                AND rie.snapshot->>'claim_id'=CAST(ric.object_id AS text)
                AND rie.snapshot->>'source_anchor_id'=CAST(sa.id AS text)
                AND NOT EXISTS (SELECT 1 FROM source_invalidations si
                    WHERE si.source_version_id=sv.id AND si.tenant_id=:tenant)
            ORDER BY er.claim_id,er.created_at
        """).bindparams(bindparam("ids", expanding=True))
        rows = (
            (
                await connection.execute(
                    statement,
                    {"release": release_id, "tenant": principal.tenant_id, "ids": claim_ids},
                )
            )
            .mappings()
            .all()
        )
        clearance = CLASSIFICATION_LEVEL[principal.clearance.value]
        return [
            {
                "id": str(new_uuid7()),
                "release_id": str(release_id),
                "evidence_id": str(row["evidence_id"]),
                "source_version_id": str(row["source_version_id"]),
                "source_anchor_id": str(row["source_anchor_id"]),
                "claim_id": str(row["claim_id"]) if row["claim_id"] else None,
                "relation_id": str(row["relation_id"]) if row["relation_id"] else None,
                "excerpt": None,
                "locator": {"locators": row["locators"]},
                "status": "VALID",
            }
            for row in rows
            if row["current_claim_level"] is not None
            and row["current_claim_level"] <= clearance
            and all(
                CLASSIFICATION_LEVEL[str(row[k])] <= clearance
                for k in ("classification", "document_classification", "claim_classification")
            )
        ]

    async def _supported_hits(
        self,
        connection: AsyncConnection,
        release_id: UUID,
        hits: list[dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ids = {UUID(str(c["claim_id"])) for c in citations if c.get("claim_id")}
        if not ids:
            return []
        query = text(
            "SELECT object_id,snapshot FROM release_items WHERE release_id=:release AND object_type='CLAIM' AND object_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        rows = (
            (await connection.execute(query, {"release": release_id, "ids": list(ids)}))
            .mappings()
            .all()
        )
        frozen = {str(r["object_id"]): dict(r["snapshot"]) for r in rows}
        return [
            {**hit, "text": frozen[str(hit["object_id"])]["statement"], "title": "已发布主张"}
            for hit in hits
            if hit["object_type"] == "CLAIM" and str(hit["object_id"]) in frozen
        ]

    async def get_query_answer(self, *, principal: Principal, answer_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            answer = (
                (
                    await connection.execute(
                        text("SELECT * FROM query_answers WHERE tenant_id=:tenant AND id=:id"),
                        {"tenant": principal.tenant_id, "id": answer_id},
                    )
                )
                .mappings()
                .first()
            )
            if answer is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "QueryAnswer unavailable",
                    "The QueryAnswer is unavailable.",
                )
            citations = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,release_id,evidence_id,source_version_id,source_anchor_id,claim_id,relation_id,excerpt,locator,status FROM citations WHERE answer_id=:id ORDER BY created_at"
                        ),
                        {"id": answer_id},
                    )
                )
                .mappings()
                .all()
            )
        await self.authorize_space(
            principal=principal,
            space_id=UUID(str(answer["space_id"])),
            action="query.answer.read",
            trace_id=str(new_uuid7()),
        )
        async with self._database.engine.connect() as connection:
            policy = (
                await connection.execute(
                    text("SELECT policy_snapshot FROM query_sessions WHERE id=:id"),
                    {"id": answer["query_session_id"]},
                )
            ).scalar_one()
            if CLASSIFICATION_LEVEL[principal.clearance.value] < CLASSIFICATION_LEVEL.get(
                policy.get("clearance"), 3
            ):
                raise ApiProblem(
                    403,
                    "ACCESS_DENIED",
                    "Answer unavailable",
                    "Current clearance does not allow this answer.",
                )
            old = [dict(c) for c in citations]
            hits = [
                {"object_id": str(c["claim_id"]), "object_type": "CLAIM"}
                for c in old
                if c["claim_id"]
            ]
            visible = await self._visible_citations(
                connection, principal, UUID(str(answer["release_id"])), hits
            )
            valid = {
                (c["evidence_id"], c["source_anchor_id"], c["source_version_id"], c["claim_id"])
                for c in visible
            }
            kept = [
                _json_value(c)
                for c in old
                if tuple(
                    str(c[k])
                    for k in ("evidence_id", "source_anchor_id", "source_version_id", "claim_id")
                )
                in valid
            ]
            supported = await self._supported_hits(
                connection, UUID(str(answer["release_id"])), hits, kept
            )
        statements = list(dict.fromkeys(str(h["text"]) for h in supported))[:3]
        direct = (
            "；".join(statements)
            if statements
            else "当前固定 Release 中没有足够的可见有效证据，无法下结论。"
        )
        return _json_value(
            {
                **answer,
                "status": "COMPLETED" if statements else "REFUSED",
                "direct_answer": direct,
                "key_basis": statements,
                "conflicts": [],
                "retrieval_hits": [],
                "citations": kept,
                "read_checked_at": datetime.now(UTC),
                "read_filtered": direct != answer["direct_answer"] or len(kept) != len(old),
                "uncertainty": "按当前权限与来源有效性重新核验；原始答案记录未修改。冲突需在有权限的冲突工作台另行核查。",
            }
        )

    async def traverse_graph(
        self,
        *,
        principal: Principal,
        release_id: UUID,
        start_entity_id: UUID,
        target_entity_id: UUID | None,
        mode: str,
        max_depth: int,
        causal_only: bool,
        as_of: datetime | None,
    ) -> JsonDict:
        from nexweave_api.release_graph import read_graph

        release = await self.get_release(principal=principal, release_id=release_id)
        await self.authorize_space(
            principal=principal,
            space_id=UUID(str(release["space_id"])),
            action="graph.read",
            trace_id=str(new_uuid7()),
        )
        async with self._database.engine.connect() as connection:
            graph = await read_graph(
                connection,
                principal,
                release_id,
                start_entity_id,
                target_entity_id,
                mode,
                max_depth,
                causal_only,
                as_of,
            )
        return {
            "release_id": str(release_id),
            "start_entity_id": str(start_entity_id),
            "target_entity_id": str(target_entity_id) if target_entity_id else None,
            "mode": mode,
            **graph,
        }
