"""M9.5 persistence adapter composed with the existing authorization boundary."""
# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from secrets import token_hex
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.database import Database
from nexweave_api.errors import ApiProblem
from nexweave_api.integration_repository import IntegrationRepository
from nexweave_api.repository import _json_value
from nexweave_api.settings import Settings
from nexweave_contracts.forecast import BindingCreate, ForecastCreate
from nexweave_domain import DataClassification, Principal, new_uuid7
from nexweave_domain.access import CLASSIFICATION_LEVEL, ActorType


class ForecastRepository:
    def __init__(self, database: Database, platform: IntegrationRepository, settings: Settings):
        self.database, self.platform, self.settings = database, platform, settings

    async def authorize(
        self, principal: Principal, space_id: UUID, action: str, classification: str | None = None
    ) -> None:
        await self.platform.authorize_space(
            principal=principal,
            space_id=space_id,
            action=action,
            trace_id=token_hex(16),
            classification=DataClassification(classification) if classification else None,
        )

    async def binding_entities(self, principal: Principal, space_id: UUID) -> list[dict[str, Any]]:
        await self.authorize(principal, space_id, "governance.manage")
        async with self.database.engine.connect() as c:
            rows = (
                (
                    await c.execute(
                        text("""SELECT ke.id,ke.schema_version_id,ke.type_key,ke.display_name,
                (SELECT max(CASE sv.classification WHEN 'HIGHLY_RESTRICTED' THEN 3
                 WHEN 'CONFIDENTIAL' THEN 2 WHEN 'INTERNAL' THEN 1 ELSE 0 END)
                 FROM compile_job_sources cs JOIN source_versions sv ON sv.id=cs.source_version_id
                 WHERE cs.compile_job_id=ev.compile_job_id) AS clearance
                FROM knowledge_entities ke JOIN knowledge_entity_versions ev ON ev.id=ke.current_version_id
                JOIN schema_versions sc ON sc.id=ke.schema_version_id AND sc.status='PUBLISHED'
                WHERE ke.tenant_id=:tenant AND ke.space_id=:space ORDER BY ke.display_name,ke.id"""),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [
            _json_value({k: r[k] for k in ("id", "schema_version_id", "type_key", "display_name")})
            for r in rows
            if r["clearance"] is not None
            and r["clearance"] <= CLASSIFICATION_LEVEL[principal.clearance]
        ]

    async def prepare_binding(
        self, principal: Principal, space_id: UUID, body: BindingCreate
    ) -> dict[str, Any]:
        await self.authorize(principal, space_id, "governance.manage")
        async with self.database.engine.connect() as c:
            schema = (
                (
                    await c.execute(
                        text(
                            "SELECT * FROM schema_versions WHERE id=:id AND tenant_id=:tenant AND space_id=:space AND status='PUBLISHED'"
                        ),
                        {
                            "id": body.schema_version_id,
                            "tenant": principal.tenant_id,
                            "space": space_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            entity = (
                (
                    await c.execute(
                        text(
                            "SELECT ke.id,ke.type_key,ke.display_name,ke.schema_version_id,(SELECT sv.classification FROM compile_job_sources cs JOIN source_versions sv ON sv.id=cs.source_version_id WHERE cs.compile_job_id=ev.compile_job_id ORDER BY CASE sv.classification WHEN 'HIGHLY_RESTRICTED' THEN 3 WHEN 'CONFIDENTIAL' THEN 2 WHEN 'INTERNAL' THEN 1 ELSE 0 END DESC LIMIT 1) AS classification FROM knowledge_entities ke JOIN knowledge_entity_versions ev ON ev.id=ke.current_version_id WHERE ke.id=:id AND ke.tenant_id=:tenant AND ke.space_id=:space"
                        ),
                        {"id": body.entity_id, "tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .first()
            )
            source = (
                (
                    await c.execute(
                        text(
                            "SELECT sv.* FROM source_versions sv JOIN parse_jobs pj ON pj.id=sv.active_parse_job_id WHERE sv.id=:id AND sv.tenant_id=:tenant AND sv.space_id=:space AND pj.malware_scan_status='CLEAN' AND sv.status NOT IN ('INVALIDATED','REJECTED','ARCHIVED')"
                        ),
                        {
                            "id": body.source_version_id,
                            "tenant": principal.tenant_id,
                            "space": space_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
        if (
            not schema
            or not entity
            or not source
            or entity["schema_version_id"] != body.schema_version_id
        ):
            raise ApiProblem(
                422,
                "BINDING_INPUT_UNAVAILABLE",
                "Binding unavailable",
                "Use a published Schema, scoped entity and clean parsed SourceVersion.",
            )
        classification = str(source["classification"])
        facts = await self.platform.get_space_facts(space_id, principal)
        classification = max(
            (classification, facts.classification.value, str(entity["classification"])),
            key=lambda s: CLASSIFICATION_LEVEL[DataClassification(s)],
        )
        await self.authorize(principal, space_id, "source.read", classification)
        if source["content_type"] != "text/csv" or source["size"] > 2_000_000:
            raise ApiProblem(
                422, "SOURCE_TYPE_UNSUPPORTED", "CSV required", "Use a UTF-8 CSV under 2 MB."
            )
        snapshot = schema["normalized_snapshot"]
        profiles = {p["key"]: p for p in snapshot.get("forecastProfiles", [])}
        profile = profiles.get(body.profile_key)
        if not profile:
            raise ApiProblem(
                422,
                "PROFILE_UNAVAILABLE",
                "Profile unavailable",
                "Schema has no matching forecast profile.",
            )
        signals = {s["key"]: s for s in snapshot["signalDefinitions"]}
        columns = {c.signal_key: c for c in body.columns}
        required = {profile["target"], *profile["pastCovariates"], *profile["futureCovariates"]}
        if (
            set(columns) != required
            or len(columns) != len(body.columns)
            or len({c.column for c in body.columns}) != len(columns)
        ):
            raise ApiProblem(
                422,
                "BINDING_AMBIGUOUS",
                "Binding ambiguous",
                "Bind every profile signal to one distinct CSV column.",
            )
        if any(
            signals[k]["unit"] != columns[k].unit or signals[k]["typeKey"] != entity["type_key"]
            for k in required
        ):
            raise ApiProblem(
                422,
                "UNIT_OR_TYPE_MISMATCH",
                "Binding mismatch",
                "Signal unit/type differs from the entity or schema.",
            )
        record = body.model_dump(mode="json")
        record.update(
            id=str(new_uuid7()),
            tenant_id=str(principal.tenant_id),
            space_id=str(space_id),
            classification=classification,
            status="ACTIVE",
            version=1,
            created_at=datetime.now(UTC).isoformat(),
        )
        record["snapshot"] = {
            "profile": profile,
            "signals": [signals[k] for k in sorted(required)],
            "source_checksum": source["checksum"],
            "object_key": source["object_key"],
            "object_version_id": source["object_version_id"],
            "schema_checksum": schema["composition_checksum"],
            "entity": _json_value(dict(entity)),
        }

        return record

    async def create_binding(
        self, principal: Principal, space_id: UUID, body: BindingCreate, key: str, trace_id: str
    ) -> dict[str, Any]:
        record = await self.prepare_binding(principal, space_id, body)
        classification = record["classification"]

        async def mutation(c: AsyncConnection) -> dict[str, Any]:
            await c.execute(
                text(
                    "INSERT INTO signal_bindings(id,tenant_id,space_id,entity_id,schema_version_id,source_version_id,classification,body,created_by) VALUES(:id,:tenant,:space,:entity,:schema,:source,:classification,CAST(:body AS jsonb),:actor)"
                ),
                {
                    "id": UUID(record["id"]),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "entity": body.entity_id,
                    "schema": body.schema_version_id,
                    "source": body.source_version_id,
                    "classification": classification,
                    "body": json.dumps(record),
                    "actor": principal.actor_id,
                },
            )
            await self.audit(
                c,
                principal,
                space_id,
                "signal-binding.activated",
                UUID(record["id"]),
                trace_id,
                {"source_version_id": str(body.source_version_id)},
            )
            return record

        return await self.platform._idempotent(
            principal=principal,
            operation=f"forecast.binding:{space_id}",
            key=key,
            request=body.model_dump(mode="json"),
            mutation=mutation,
        )

    async def list_bindings(self, principal: Principal, space_id: UUID) -> list[dict[str, Any]]:
        await self.authorize(principal, space_id, "knowledge.read")
        async with self.database.engine.connect() as c:
            rows = (
                (
                    await c.execute(
                        text(
                            "SELECT body,classification FROM signal_bindings WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC LIMIT 100"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [
            dict(r["body"])
            for r in rows
            if CLASSIFICATION_LEVEL[r["classification"]]
            <= CLASSIFICATION_LEVEL[principal.clearance]
        ]

    async def get_binding(self, principal: Principal, binding_id: UUID) -> dict[str, Any]:
        async with self.database.engine.connect() as c:
            row = (
                await c.execute(
                    text("SELECT body FROM signal_bindings WHERE tenant_id=:tenant AND id=:id"),
                    {"tenant": principal.tenant_id, "id": binding_id},
                )
            ).scalar_one_or_none()
        if not row:
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "Not found", "Binding unavailable.")
        await self.authorize(
            principal, UUID(row["space_id"]), "knowledge.read", row["classification"]
        )
        return dict(row)

    async def create_run(
        self,
        principal: Principal,
        space_id: UUID,
        body: ForecastCreate,
        key: str,
        trace_id: str,
        *,
        retry_from: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        binding = await self.get_binding(principal, body.binding_id)
        if binding["space_id"] != str(space_id):
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Not found", "Binding unavailable in space."
            )
        await self.authorize(principal, space_id, "compile.create", binding["classification"])
        if body.horizon > binding["snapshot"]["profile"]["maxHorizon"]:
            raise ApiProblem(
                422, "FORECAST_HORIZON_EXCEEDED", "Horizon exceeded", "Profile horizon exceeded."
            )
        if body.release_id:
            release = await self.platform.get_release(
                principal=principal, release_id=body.release_id
            )
            if str(release["space_id"]) != str(space_id):
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Not found", "Release unavailable in space."
                )
        run_id = new_uuid7()
        request = body.model_dump(mode="json")
        actor = {
            "tenant_id": str(principal.tenant_id),
            "actor_id": str(principal.actor_id),
            "actor_type": principal.actor_type.value,
            "subject": principal.subject,
            "clearance": principal.clearance.value,
        }

        async def mutation(c: AsyncConnection) -> dict[str, Any]:
            await c.execute(
                text(
                    "INSERT INTO forecast_runs(id,tenant_id,space_id,binding_id,classification,request,principal_snapshot,model_revision,workflow_id,created_by,context) VALUES(:id,:tenant,:space,:binding,:classification,CAST(:request AS jsonb),CAST(:principal AS jsonb),:revision,:workflow,:actor,CAST(:context AS jsonb))"
                ),
                {
                    "id": run_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "binding": body.binding_id,
                    "classification": binding["classification"],
                    "request": json.dumps(request),
                    "principal": json.dumps(actor),
                    "revision": retry_from["model_revision"]
                    if retry_from
                    else (
                        self.settings.forecast_model_revision
                        if body.provider_id == "chronos2"
                        else "persistence/1"
                    ),
                    "context": json.dumps(retry_from["context"])
                    if retry_from and retry_from["context"] is not None
                    else None,
                    "workflow": f"nexweave.forecast.v2:{run_id}",
                    "actor": principal.actor_id,
                },
            )
            await c.execute(
                text(
                    "INSERT INTO forecast_delivery(run_id,workflow_name,trace_id,retry_of) VALUES(:id,'nexweave.forecast.v2',:trace,:retry)"
                ),
                {
                    "id": run_id,
                    "trace": trace_id,
                    "retry": UUID(retry_from["id"]) if retry_from else None,
                },
            )
            await self.audit(
                c,
                principal,
                space_id,
                "forecast.queued",
                run_id,
                trace_id,
                {
                    "binding_id": str(body.binding_id),
                    "provider_id": body.provider_id,
                    **({"retry_of": retry_from["id"], "reason": reason} if retry_from else {}),
                },
            )
            return {"id": str(run_id)}

        created = await self.platform._idempotent(
            principal=principal,
            operation=f"forecast.retry:{retry_from['id']}"
            if retry_from
            else f"forecast.run:{space_id}",
            key=key,
            request={"forecast": request, "reason": reason} if retry_from else request,
            mutation=mutation,
        )
        return await self.get_run(principal, UUID(created["id"]))

    async def raw_run(self, run_id: UUID) -> dict[str, Any]:
        async with self.database.engine.connect() as c:
            row = (
                (
                    await c.execute(
                        text(
                            "SELECT r.*,d.status AS delivery_status,d.attempts AS delivery_attempts,d.error_code AS delivery_error_code,d.retry_of FROM forecast_runs r JOIN forecast_delivery d ON d.run_id=r.id WHERE r.id=:id"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .first()
            )
        if not row:
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "Not found", "Run unavailable.")
        return _json_value(dict(row))

    async def worker_principal(self, run: dict[str, Any]) -> Principal:
        s = run["principal_snapshot"]
        return await self.platform.resolve_principal(
            Principal(
                tenant_id=UUID(s["tenant_id"]),
                actor_id=UUID(s["actor_id"]),
                actor_type=ActorType(s["actor_type"]),
                subject=s["subject"],
                audience=("nexweave-api",),
                tenant_roles=frozenset(),
                token_id="forecast-worker",  # noqa: S106 - audit origin, not a credential
                clearance=DataClassification(s["clearance"]),
            )
        )

    async def get_run(self, principal: Principal, run_id: UUID) -> dict[str, Any]:
        run = await self.raw_run(run_id)
        if run["tenant_id"] != str(principal.tenant_id):
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "Not found", "Run unavailable.")
        await self.authorize(
            principal, UUID(run["space_id"]), "knowledge.read", run["classification"]
        )
        return {
            k: run[k]
            for k in (
                "id",
                "tenant_id",
                "space_id",
                "binding_id",
                "status",
                "workflow_id",
                "delivery_status",
                "delivery_attempts",
                "delivery_error_code",
                "retry_of",
                "artifact_id",
                "error_code",
                "request",
                "created_at",
                "updated_at",
            )
        }

    async def list_runs(self, principal: Principal, space_id: UUID) -> list[dict[str, Any]]:
        await self.authorize(principal, space_id, "knowledge.read")
        async with self.database.engine.connect() as c:
            rows = (
                (
                    await c.execute(
                        text(
                            "SELECT r.*,d.status AS delivery_status,d.attempts AS delivery_attempts,d.error_code AS delivery_error_code,d.retry_of FROM forecast_runs r JOIN forecast_delivery d ON d.run_id=r.id WHERE r.tenant_id=:tenant AND r.space_id=:space ORDER BY r.created_at DESC LIMIT 100"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        keys = (
            "id",
            "tenant_id",
            "space_id",
            "binding_id",
            "status",
            "workflow_id",
            "delivery_status",
            "delivery_attempts",
            "delivery_error_code",
            "retry_of",
            "artifact_id",
            "error_code",
            "request",
            "created_at",
            "updated_at",
        )
        return [
            _json_value({k: r[k] for k in keys})
            for r in rows
            if CLASSIFICATION_LEVEL[r["classification"]]
            <= CLASSIFICATION_LEVEL[principal.clearance]
        ]

    async def get_artifact(self, principal: Principal, artifact_id: UUID) -> dict[str, Any]:
        async with self.database.engine.connect() as c:
            row = (
                (
                    await c.execute(
                        text("SELECT * FROM forecast_artifacts WHERE id=:id AND tenant_id=:tenant"),
                        {"id": artifact_id, "tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .first()
            )
        if not row:
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "Not found", "Artifact unavailable.")
        await self.authorize(
            principal, UUID(str(row["space_id"])), "knowledge.read", row["classification"]
        )
        result = _json_value(dict(row))
        result.pop("object_key")
        result["epistemic_kind"] = "FORECAST"
        return result

    async def audit(
        self,
        c: AsyncConnection,
        principal: Principal,
        space_id: UUID,
        action: str,
        resource_id: UUID,
        trace_id: str,
        metadata: dict[str, Any],
    ) -> None:
        await self.platform._insert_audit(
            c,
            principal=principal,
            space_id=space_id,
            action=action,
            resource_type="Forecast",
            resource_id=resource_id,
            trace_id=trace_id,
            outcome="SUCCEEDED",
            metadata=metadata,
        )
        await self.platform._insert_outbox(
            c,
            principal=principal,
            event_type=f"nexweave.{action}.v1",
            aggregate_type="Forecast",
            aggregate_id=resource_id,
            aggregate_version=1,
            space_id=space_id,
            trace_id=trace_id,
            payload={"id": str(resource_id), **metadata},
        )

    async def retry_run(
        self, principal: Principal, run_id: UUID, key: str, reason: str, trace_id: str
    ) -> dict[str, Any]:
        run = await self.get_run(principal, run_id)
        if run["status"] not in {"FAILED", "CANCELLED"}:
            raise ApiProblem(
                409,
                "FORECAST_NOT_RETRYABLE",
                "Run not retryable",
                "Only failed or cancelled runs can create a retry.",
            )
        frozen = await self.raw_run(run_id)
        return await self.create_run(
            principal,
            UUID(run["space_id"]),
            ForecastCreate.model_validate(run["request"]),
            key,
            trace_id,
            retry_from=frozen,
            reason=reason,
        )

    async def cancel_run(
        self, principal: Principal, run_id: UUID, key: str, reason: str, trace_id: str
    ) -> dict[str, Any]:
        run = await self.get_run(principal, run_id)
        await self.authorize(
            principal,
            UUID(run["space_id"]),
            "compile.create",
            (await self.raw_run(run_id))["classification"],
        )

        async def mutation(c: AsyncConnection) -> dict[str, Any]:
            current = (
                await c.execute(
                    text("SELECT status FROM forecast_runs WHERE id=:id FOR UPDATE"), {"id": run_id}
                )
            ).scalar_one()
            if current in {"SUCCEEDED", "FAILED"}:
                raise ApiProblem(
                    409,
                    "FORECAST_ALREADY_TERMINAL",
                    "Run is terminal",
                    "Completed history cannot be cancelled.",
                )
            if current != "CANCELLED":
                await c.execute(
                    text(
                        "UPDATE forecast_runs SET status='CANCELLED',updated_at=now() WHERE id=:id"
                    ),
                    {"id": run_id},
                )
                await c.execute(
                    text(
                        "UPDATE forecast_delivery SET cancel_pending=true,next_attempt_at=now(),updated_at=now() WHERE run_id=:id"
                    ),
                    {"id": run_id},
                )
                await self.audit(
                    c,
                    principal,
                    UUID(run["space_id"]),
                    "forecast.cancelled",
                    run_id,
                    trace_id,
                    {"reason": reason},
                )
            return {"id": str(run_id)}

        await self.platform._idempotent(
            principal=principal,
            operation=f"forecast.cancel:{run_id}",
            key=key,
            request={"reason": reason},
            mutation=mutation,
        )
        return await self.get_run(principal, run_id)

    async def runtime_status(self, principal: Principal, space_id: UUID) -> dict[str, Any]:
        from nexweave_contracts.runtime import IMPLEMENTATION_VERSION

        await self.authorize(principal, space_id, "knowledge.read")
        async with self.database.engine.connect() as c:
            workers = (
                await c.execute(
                    text(
                        "SELECT count(*) FROM forecast_worker_leases WHERE queue=:queue AND ready AND seen_at > now()-interval '20 seconds' AND implementation_version=:version AND model_revision=:revision"
                    ),
                    {
                        "queue": self.settings.forecast_task_queue,
                        "version": IMPLEMENTATION_VERSION,
                        "revision": self.settings.forecast_model_revision,
                    },
                )
            ).scalar_one()
            rows = (
                (
                    await c.execute(
                        text(
                            "SELECT r.status,r.classification,d.status AS delivery FROM forecast_runs r JOIN forecast_delivery d ON d.run_id=r.id WHERE r.tenant_id=:tenant AND r.space_id=:space AND r.status IN ('QUEUED','RUNNING')"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        allowed = [
            r
            for r in rows
            if CLASSIFICATION_LEVEL[DataClassification(r["classification"])]
            <= CLASSIFICATION_LEVEL[principal.clearance]
        ]
        return {
            "worker_status": "AVAILABLE" if workers else "UNAVAILABLE",
            "worker_count": workers,
            "queued": sum(r["status"] == "QUEUED" for r in allowed),
            "running": sum(r["status"] == "RUNNING" for r in allowed),
            "delivery_pending": sum(r["delivery"] in {"PENDING", "RETRYING"} for r in allowed),
            "implementation_version": IMPLEMENTATION_VERSION,
        }
