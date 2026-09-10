"""Retryable, observable I/O activities for the M2 Temporal kernel."""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from nexweave_api.connector_provider import ReadOnlyConnectorProvider
from nexweave_api.errors import ApiProblem
from nexweave_api.integration_repository import IntegrationRepository
from nexweave_application import ObjectStoragePort, StoredObjectInfo
from nexweave_domain import (
    ActorType,
    CompileRuleViolation,
    DataClassification,
    Principal,
    Role,
    SemanticRuleViolation,
)


class KernelActivities:
    def __init__(
        self,
        repository: IntegrationRepository,
        object_storage: ObjectStoragePort,
        maximum_upload_bytes: int,
    ) -> None:
        self._repository = repository
        self._object_storage = object_storage
        self._connector_provider = ReadOnlyConnectorProvider(object_storage, maximum_upload_bytes)

    @activity.defn(name="record_projection_transition")
    async def record_projection_transition(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity.heartbeat(
            {
                "event_key": payload["event_key"],
                "status": payload["status"],
                "step_key": payload.get("step_key"),
            }
        )
        return await self._repository.apply_projection_event(payload)

    @activity.defn(name="execute_m2_kernel_step")
    async def execute_kernel_step(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Exercise retry semantics without implementing any M3+ business operation."""

        info = activity.info()
        activity.heartbeat(
            {
                "task_id": payload["task_id"],
                "step_key": payload["step_key"],
                "attempt": info.attempt,
            }
        )
        if "retryable-" in str(payload["step_key"]) and info.attempt == 1:
            raise ApplicationError(
                "M2 deterministic transient-failure drill",
                type="M2_INJECTED_TRANSIENT_FAILURE",
            )
        return {
            "attempt": info.attempt,
            "kernel_outcome": "STUB_SUCCEEDED",
            "step_key": payload["step_key"],
        }

    @activity.defn(name="compensate_m2_kernel_step")
    async def compensate_kernel_step(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity.heartbeat({"task_id": payload["task_id"], "step_key": payload["step_key"]})
        return {
            "kernel_outcome": "STUB_COMPENSATED",
            "step_key": payload["step_key"],
        }

    @activity.defn(name="m4_pack_resolve_compose_persist")
    async def execute_pack_installation(self, payload: dict[str, Any]) -> dict[str, Any]:
        info = activity.info()
        activity.heartbeat({"installation_id": payload["installation_id"], "attempt": info.attempt})
        try:
            return await self._repository.execute_pack_installation(
                installation_id=UUID(str(payload["installation_id"])),
                run_id=str(payload["run_id"]),
                trace_id=str(payload["trace_id"]),
            )
        except (ApiProblem, CompileRuleViolation, SemanticRuleViolation) as exc:
            code = exc.code
            raise ApplicationError(
                str(exc), type=code, non_retryable=not code.endswith("UNAVAILABLE")
            ) from exc

    @activity.defn(name="m4_pack_fail")
    async def fail_pack_installation(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._repository.fail_pack_installation(
            installation_id=UUID(str(payload["installation_id"])),
            code=str(payload["code"]),
            actor_id=UUID(str(payload["actor_id"])),
            trace_id=str(payload["trace_id"]),
        )
        return {"status": "FAILED", "code": str(payload["code"])}

    @activity.defn(name="m5_compile_execute")
    async def execute_compile(self, payload: dict[str, Any]) -> dict[str, Any]:
        info = activity.info()
        activity.heartbeat({"compile_job_id": payload["compile_job_id"], "attempt": info.attempt})
        try:
            return await self._repository.execute_compile(
                compile_job_id=UUID(str(payload["compile_job_id"])),
                run_id=str(payload["run_id"]),
                trace_id=str(payload["trace_id"]),
            )
        except (ApiProblem, CompileRuleViolation, SemanticRuleViolation) as exc:
            code = exc.code
            raise ApplicationError(
                str(exc), type=code, non_retryable=not code.endswith("UNAVAILABLE")
            ) from exc

    @activity.defn(name="m5_compile_fail")
    async def fail_compile(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._repository.fail_compile(
            compile_job_id=UUID(str(payload["compile_job_id"])),
            code=str(payload["code"]),
            detail=str(payload.get("detail", "Compile Activity failed")),
            trace_id=str(payload["trace_id"]),
        )
        return {"status": "FAILED", "code": str(payload["code"])}

    @activity.defn(name="m7_quality_evaluate")
    async def execute_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity.heartbeat({"evaluation_run_id": payload["evaluation_run_id"]})
        return await self._repository.execute_evaluation_run(
            run_id=UUID(str(payload["evaluation_run_id"]))
        )

    @activity.defn(name="m7_release_validate")
    async def validate_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity.heartbeat({"release_candidate_id": payload["release_candidate_id"]})
        return await self._repository.execute_release_validation(
            candidate_id=UUID(str(payload["release_candidate_id"])),
            trace_id=str(payload["trace_id"]),
        )

    @activity.defn(name="m7_release_publish")
    async def publish_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity.heartbeat({"release_candidate_id": payload["release_candidate_id"]})
        try:
            return await self._repository.publish_approved_release(
                candidate_id=UUID(str(payload["release_candidate_id"])),
                approver_id=UUID(str(payload["approver_id"])),
                trace_id=str(payload["trace_id"]),
            )
        except ApiProblem as exc:
            raise ApplicationError(str(exc), type=exc.code, non_retryable=True) from exc

    @activity.defn(name="m8_connector_read_register_raw")
    async def read_connector_and_register_raw(self, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = UUID(str(payload["connector_sync_run_id"]))
        activity.heartbeat({"connector_sync_run_id": str(run_id)})
        try:
            context = await self._repository.connector_sync_context(run_id=run_id)
            filename, content_type, content, locator = await self._connector_provider.read(context)
            checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
            principal = Principal(
                actor_type=ActorType.USER,
                actor_id=UUID(str(context["created_by"])),
                tenant_id=UUID(str(context["tenant_id"])),
                subject="connector-sync",
                audience=("nexweave-api",),
                tenant_roles=frozenset({Role.SPACE_ADMIN}),
                clearance=DataClassification(str(context["classification"])),
                token_id=f"connector-sync:{run_id}",
            )
            session = await self._repository.create_source_upload(
                principal=principal,
                space_id=UUID(str(context["space_id"])),
                payload={
                    "filename": filename,
                    "content_type": content_type,
                    "expected_size": len(content),
                    "expected_checksum": checksum,
                    "display_name": str(context["config"].get("display_name", filename)),
                    "description": f"Read-only Connector {context['connector_name']}",
                    "classification": str(context["classification"]),
                    "tags": ("connector", str(context["kind"]).casefold()),
                },
                idempotency_key=f"connector:{run_id}:{checksum}",
                ttl_seconds=900,
                trace_id=str(payload["trace_id"]),
            )
            info = await self._object_storage.put_if_absent(
                key=str(session["object_key"]),
                content=content,
                content_type=content_type,
                checksum_sha256=checksum,
            )
            await self._repository.mark_source_content_uploaded(
                principal=principal,
                upload_id=UUID(str(session["id"])),
                info=info,
                trace_id=str(payload["trace_id"]),
            )
            result = await self._repository.register_raw_and_parse_job(
                principal=principal,
                upload_id=UUID(str(session["id"])),
                verified_info=StoredObjectInfo(
                    key=info.key,
                    version_id=info.version_id,
                    size=info.size,
                    checksum_sha256=info.checksum_sha256,
                    content_type=info.content_type,
                ),
                idempotency_key=f"connector-complete:{run_id}:{checksum}",
                trace_id=str(payload["trace_id"]),
            )
            return {
                "parse_job_id": str(result["parse_job_id"]),
                "source_version_id": str(result["source_version_id"]),
                "parse_workflow_id": str(result["workflow_id"]),
                "watermark": {"checksum": checksum, "locator": locator},
            }
        except ApiProblem as exc:
            await self._repository.complete_connector_sync_run(
                run_id=run_id,
                status="FAILED",
                resulting_watermark={},
                result_summary={},
                error_code=exc.code,
            )
            raise ApplicationError(
                str(exc), type=exc.code, non_retryable=not exc.code.endswith("UNAVAILABLE")
            ) from exc

    @activity.defn(name="m8_connector_complete")
    async def complete_connector_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._repository.complete_connector_sync_run(
            run_id=UUID(str(payload["connector_sync_run_id"])),
            status="SUCCEEDED",
            resulting_watermark=dict(payload["watermark"]),
            result_summary={
                "source_version_id": payload["source_version_id"],
                "parse_job_id": payload["parse_job_id"],
            },
        )
