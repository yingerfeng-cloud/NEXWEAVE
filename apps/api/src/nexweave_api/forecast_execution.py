"""Retryable forecast activity service: all network, model and persistence I/O lives here."""

# ruff: noqa: E501 - SQL adapter statements
from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import text

from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_gateway import CsvTimeSeriesConnector, ForecastModelGateway
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.object_storage import S3ObjectStorage
from nexweave_domain import new_uuid7
from nexweave_domain.forecast import (
    build_observation_window,
    interpret_forecast,
    validate_forecast_result,
)


class ForecastExecution:
    def __init__(
        self,
        repository: ForecastRepository,
        storage: S3ObjectStorage,
        gateway: ForecastModelGateway,
    ) -> None:
        self.repository, self.storage, self.gateway = repository, storage, gateway

    async def inputs(self, run: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        principal = await self.repository.worker_principal(run)
        binding = await self.repository.get_binding(principal, UUID(run["binding_id"]))
        await self.repository.authorize(
            principal, UUID(run["space_id"]), "compile.create", binding["classification"]
        )
        await self.repository.authorize(
            principal, UUID(run["space_id"]), "source.read", binding["classification"]
        )
        if await self.repository.platform.is_source_version_invalidated(
            principal=principal, version_id=UUID(binding["source_version_id"])
        ):
            raise ApiProblem(
                422,
                "SOURCE_UNAVAILABLE",
                "Source invalidated",
                "Invalidated source cannot be used for a new prediction.",
            )
        async with self.repository.database.engine.connect() as c:
            usable = (
                await c.execute(
                    text("""SELECT 1 FROM source_versions sv
                JOIN parse_jobs pj ON pj.id=sv.active_parse_job_id
                JOIN source_documents sd ON sd.id=sv.source_document_id
                WHERE sv.id=:id AND sv.tenant_id=:tenant AND sv.space_id=:space
                AND sv.status NOT IN ('INVALIDATED','REJECTED','ARCHIVED')
                AND pj.malware_scan_status='CLEAN' AND sd.status<>'ARCHIVED' AND sv.checksum=:checksum"""),
                    {
                        "id": UUID(binding["source_version_id"]),
                        "tenant": principal.tenant_id,
                        "space": UUID(run["space_id"]),
                        "checksum": binding["snapshot"]["source_checksum"],
                    },
                )
            ).scalar()
        if not usable:
            raise ApiProblem(
                422,
                "SOURCE_UNAVAILABLE",
                "Source unavailable",
                "Source was invalidated or quarantined.",
            )
        return principal, binding

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        repo = self.repository
        run_id = UUID(payload["run_id"])
        run = await repo.raw_run(run_id)
        if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return {"status": run["status"], "artifact_id": run["artifact_id"]}
        principal, binding = await self.inputs(run)
        if (
            run["request"]["provider_id"] == "chronos2"
            and run["model_revision"] != repo.settings.forecast_model_revision
        ):
            raise ApiProblem(
                422,
                "MODEL_REVISION_MISMATCH",
                "Model unavailable",
                "Worker model revision differs from frozen run.",
            )
        context = run["context"]
        if context is None:
            connector = CsvTimeSeriesConnector(
                self.storage, binding["snapshot"].get("object_version_id")
            )
            raw = await connector.read_window(
                binding["snapshot"]["object_key"], binding["snapshot"]["source_checksum"]
            )
            context = build_observation_window(raw, binding, run["request"])
        async with repo.database.engine.begin() as c:
            row = (
                (
                    await c.execute(
                        text("SELECT status,context FROM forecast_runs WHERE id=:id FOR UPDATE"),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            if row["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return {"status": row["status"]}
            if row["context"] is not None:
                context = row["context"]
            if row["status"] == "QUEUED":
                await c.execute(
                    text(
                        "UPDATE forecast_runs SET status='RUNNING',context=CAST(:context AS jsonb),updated_at=now() WHERE id=:id"
                    ),
                    {"id": run_id, "context": json.dumps(context)},
                )
                await repo.audit(
                    c,
                    principal,
                    UUID(run["space_id"]),
                    "forecast.started",
                    run_id,
                    payload["trace_id"],
                    {},
                )
        result = await self.gateway.forecast(run["request"]["provider_id"], context)
        validate_forecast_result(result, run["request"]["horizon"])
        interpretation = interpret_forecast(context, result, run["request"].get("event_rule"))
        # Knowledge lookup remains explicitly separate from the numerical prediction.
        released_knowledge: dict[str, Any] = {"status": "NO_RELEASE_SELECTED", "citations": []}
        if run["request"].get("release_id"):
            release = await repo.platform.get_release(
                principal=principal, release_id=UUID(run["request"]["release_id"])
            )
            released_knowledge = {
                "status": "RELEASE_REFERENCE_ONLY",
                "release_id": str(release["id"]),
                "citations": [],
            }
        content = {
            "contract_version": "nexweave.forecast-artifact/1",
            "epistemic_kind": "FORECAST",
            "run_id": str(run_id),
            "binding_id": run["binding_id"],
            "context": context,
            "result": result,
            **interpretation,
            "released_knowledge": released_knowledge,
        }
        raw_artifact = json.dumps(
            content, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
        checksum = "sha256:" + hashlib.sha256(raw_artifact).hexdigest()
        object_key = f"tenants/{run['tenant_id']}/spaces/{run['space_id']}/forecasts/{run_id}/{checksum[7:]}.json"
        await self.storage.put_if_absent(
            key=object_key,
            content=raw_artifact,
            content_type="application/json",
            checksum_sha256=checksum,
        )
        principal, _ = await self.inputs(run)
        artifact_id = new_uuid7()
        async with repo.database.engine.begin() as c:
            current = (
                (
                    await c.execute(
                        text(
                            "SELECT status,artifact_id FROM forecast_runs WHERE id=:id FOR UPDATE"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            if current["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return {
                    "status": current["status"],
                    "artifact_id": str(current["artifact_id"]) if current["artifact_id"] else None,
                }
            await c.execute(
                text("""INSERT INTO forecast_artifacts(id,tenant_id,space_id,run_id,classification,data_kind,content_checksum,object_key,content)
                VALUES(:id,:tenant,:space,:run,:classification,:kind,:checksum,:key,CAST(:content AS jsonb))"""),
                {
                    "id": artifact_id,
                    "tenant": principal.tenant_id,
                    "space": UUID(run["space_id"]),
                    "run": run_id,
                    "classification": run["classification"],
                    "kind": context["data_kind"],
                    "checksum": checksum,
                    "key": object_key,
                    "content": raw_artifact.decode(),
                },
            )
            await c.execute(
                text(
                    "UPDATE forecast_runs SET status='SUCCEEDED',artifact_id=:artifact,updated_at=now() WHERE id=:id"
                ),
                {"id": run_id, "artifact": artifact_id},
            )
            await repo.audit(
                c,
                principal,
                UUID(run["space_id"]),
                "forecast.completed",
                run_id,
                payload["trace_id"],
                {"artifact_id": str(artifact_id), "content_checksum": checksum},
            )
        return {"status": "SUCCEEDED", "artifact_id": str(artifact_id)}

    async def fail(self, payload: dict[str, Any]) -> None:
        run = await self.repository.raw_run(UUID(payload["run_id"]))
        if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return
        # Retain the originating actor for audit even if their permission was revoked.
        from nexweave_domain import DataClassification, Principal
        from nexweave_domain.access import ActorType

        s = run["principal_snapshot"]
        principal = Principal(
            ActorType(s["actor_type"]),
            UUID(s["actor_id"]),
            UUID(s["tenant_id"]),
            s["subject"],
            ("nexweave-api",),
            frozenset(),
            DataClassification(s["clearance"]),
            "forecast-worker",
        )
        async with self.repository.database.engine.begin() as c:
            changed = (
                await c.execute(
                    text(
                        "UPDATE forecast_runs SET status=:terminal,error_code=:error,updated_at=now() WHERE id=:id AND status IN ('QUEUED','RUNNING') RETURNING id"
                    ),
                    {
                        "id": UUID(run["id"]),
                        "error": payload["error_code"],
                        "terminal": "CANCELLED"
                        if payload.get("terminal_status") == "CANCELLED"
                        else "FAILED",
                    },
                )
            ).scalar()
            if changed:
                await self.repository.audit(
                    c,
                    principal,
                    UUID(run["space_id"]),
                    "forecast.cancelled"
                    if payload.get("terminal_status") == "CANCELLED"
                    else "forecast.failed",
                    UUID(run["id"]),
                    payload["trace_id"],
                    {"error_code": payload["error_code"]},
                )
