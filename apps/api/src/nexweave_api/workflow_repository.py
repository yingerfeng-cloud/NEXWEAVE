"""PostgreSQL projection adapter for the M2 Temporal workflow kernel."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import JsonDict, PlatformRepository, _json_value
from nexweave_application import canonical_request_hash
from nexweave_domain import (
    WORKFLOW_STEP_PLAN,
    Principal,
    WorkflowCommand,
    WorkflowTaskStatus,
    WorkflowType,
    new_uuid7,
    stable_workflow_id,
)

TASK_COLUMNS = (
    "id, tenant_id, space_id, workflow_type, business_key, display_name, workflow_id, "
    "temporal_run_id, status, version, progress, current_step, input_refs, result_summary, "
    "error_code, error_detail, projection_revision, projection_in_sync, last_reconciled_at, "
    "created_at, created_by, updated_at, updated_by"
)


class WorkflowRepository(PlatformRepository):
    async def create_workflow_task(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        workflow_type = WorkflowType(str(payload["workflow_type"]))
        business_key = str(payload["business_key"])
        workflow_id = stable_workflow_id(workflow_type, principal.tenant_id, business_key)
        request = {"space_id": space_id, **payload}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            existing = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {TASK_COLUMNS}, start_paused FROM workflow_tasks "  # noqa: S608
                            "WHERE tenant_id = :tenant AND space_id = :space "
                            "AND workflow_type = :workflow_type AND business_key = :business_key"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "workflow_type": workflow_type.value,
                            "business_key": business_key,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                same_request = (
                    existing["display_name"] == payload["display_name"]
                    and dict(existing["input_refs"]) == dict(payload["input_refs"])
                    and existing["start_paused"] == bool(payload["start_paused"])
                )
                if not same_request:
                    raise ApiProblem(
                        409,
                        "BUSINESS_KEY_CONFLICT",
                        "Workflow business key conflict",
                        "The business key is already mapped to a different workflow request.",
                    )
                return _task_value(existing)

            task_id, now = new_uuid7(), datetime.now(UTC)
            await connection.execute(
                text(
                    "INSERT INTO workflow_tasks "
                    "(id, tenant_id, space_id, workflow_type, business_key, display_name, "
                    "workflow_id, status, version, progress, input_refs, start_paused, "
                    "projection_revision, projection_in_sync, created_at, created_by, "
                    "updated_at, updated_by) VALUES "
                    "(:id, :tenant, :space, :workflow_type, :business_key, :display_name, "
                    ":workflow_id, 'CREATED', 1, 0, CAST(:input_refs AS jsonb), :start_paused, "
                    "0, false, :now, :actor, :now, :actor)"
                ),
                {
                    "id": task_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "workflow_type": workflow_type.value,
                    "business_key": business_key,
                    "display_name": payload["display_name"],
                    "workflow_id": workflow_id,
                    "input_refs": json.dumps(payload["input_refs"]),
                    "start_paused": bool(payload["start_paused"]),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            for sequence, step_key in enumerate(WORKFLOW_STEP_PLAN[workflow_type], start=1):
                await connection.execute(
                    text(
                        "INSERT INTO workflow_steps "
                        "(id, tenant_id, space_id, task_id, step_key, sequence, status, attempt, "
                        "message, updated_at) VALUES "
                        "(:id, :tenant, :space, :task, :step, :sequence, 'PENDING', 0, "
                        "'Awaiting Temporal execution', :now)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "task": task_id,
                        "step": step_key,
                        "sequence": sequence,
                        "now": now,
                    },
                )
            await self._append_workflow_event(
                connection,
                task_id=task_id,
                tenant_id=principal.tenant_id,
                space_id=space_id,
                event_key="api-created",
                event_type="TASK_CREATED",
                status=WorkflowTaskStatus.CREATED,
                step_key=None,
                message="Workflow task created; Temporal start pending",
                details={"workflow_id": workflow_id, "trace_id": trace_id},
                occurred_at=now,
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="workflow.create",
                resource_type="WorkflowTask",
                resource_id=task_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"workflow_type": workflow_type.value, "workflow_id": workflow_id},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.workflow.task.created.v1",
                aggregate_type="WorkflowTask",
                aggregate_id=task_id,
                aggregate_version=1,
                space_id=space_id,
                trace_id=trace_id,
                payload={
                    "task_id": task_id,
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type.value,
                    "status": WorkflowTaskStatus.CREATED.value,
                    "change": "CREATED",
                    "run_id": None,
                    "projection_revision": 0,
                },
            )
            return _json_value(
                {
                    "id": task_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "workflow_type": workflow_type.value,
                    "business_key": business_key,
                    "display_name": payload["display_name"],
                    "workflow_id": workflow_id,
                    "temporal_run_id": None,
                    "status": WorkflowTaskStatus.CREATED.value,
                    "version": 1,
                    "progress": 0,
                    "current_step": None,
                    "input_refs": payload["input_refs"],
                    "result_summary": {},
                    "error_code": None,
                    "error_detail": None,
                    "projection_revision": 0,
                    "projection_in_sync": False,
                    "last_reconciled_at": None,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"workflow.create:{space_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def mark_workflow_started(
        self,
        *,
        task_id: UUID,
        run_id: str,
        actor_id: UUID,
        trace_id: str,
        restarted: bool = False,
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            row = await self._task_for_update(connection, task_id)
            now = datetime.now(UTC)
            event_key = f"run:{run_id}:started"
            already = await self._workflow_event_exists(connection, task_id, event_key)
            if not already:
                await connection.execute(
                    text(
                        "UPDATE workflow_tasks SET temporal_run_id = :run, status = 'STARTING', "
                        "version = version + 1, projection_in_sync = false, updated_at = :now, "
                        "updated_by = :actor WHERE id = :id"
                    ),
                    {"run": run_id, "now": now, "actor": actor_id, "id": task_id},
                )
                await self._append_workflow_event(
                    connection,
                    task_id=task_id,
                    tenant_id=row["tenant_id"],
                    space_id=row["space_id"],
                    event_key=event_key,
                    event_type="WORKFLOW_RESTARTED" if restarted else "WORKFLOW_STARTED",
                    status=WorkflowTaskStatus.STARTING,
                    step_key=None,
                    message="Temporal run accepted",
                    details={"run_id": run_id, "trace_id": trace_id},
                    occurred_at=now,
                )
        return await self.get_workflow_task(task_id)

    async def list_workflow_tasks(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        workflow_type: WorkflowType | None = None,
        status: WorkflowTaskStatus | None = None,
    ) -> list[JsonDict]:
        conditions = ["tenant_id = :tenant", "space_id = :space"]
        params: dict[str, Any] = {"tenant": principal.tenant_id, "space": space_id}
        if workflow_type is not None:
            conditions.append("workflow_type = :workflow_type")
            params["workflow_type"] = workflow_type.value
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status.value
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {TASK_COLUMNS} FROM workflow_tasks WHERE "  # noqa: S608
                            + " AND ".join(conditions)
                            + " ORDER BY created_at DESC, id DESC"
                        ),
                        params,
                    )
                )
                .mappings()
                .all()
            )
        return [_task_value(row) for row in rows]

    async def get_workflow_task(self, task_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(f"SELECT {TASK_COLUMNS} FROM workflow_tasks WHERE id = :id"),  # noqa: S608
                        {"id": task_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Task not found", "The workflow task is unavailable."
            )
        return _task_value(row)

    async def get_workflow_task_detail(self, task_id: UUID) -> JsonDict:
        task = await self.get_workflow_task(task_id)
        async with self._database.engine.connect() as connection:
            steps = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, task_id, step_key, sequence, status, attempt, message, "
                            "started_at, completed_at, updated_at FROM workflow_steps "
                            "WHERE task_id = :task ORDER BY sequence"
                        ),
                        {"task": task_id},
                    )
                )
                .mappings()
                .all()
            )
            events = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, task_id, event_key, event_type, workflow_status, step_key, "
                            "message, details, occurred_at FROM workflow_task_events "
                            "WHERE task_id = :task ORDER BY occurred_at, id"
                        ),
                        {"task": task_id},
                    )
                )
                .mappings()
                .all()
            )
        return {
            "task": task,
            "steps": [_json_value(row) for row in steps],
            "events": [_json_value(row) for row in events],
        }

    async def assert_workflow_version(self, task_id: UUID, expected_version: int) -> JsonDict:
        task = await self.get_workflow_task(task_id)
        if task["version"] != expected_version:
            raise ApiProblem(
                412,
                "PRECONDITION_FAILED",
                "Task version changed",
                "The workflow task ETag is stale; reload before issuing a command.",
            )
        return task

    async def record_workflow_command(
        self,
        *,
        principal: Principal,
        task_id: UUID,
        command: WorkflowCommand,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
        duplicate: bool,
    ) -> JsonDict:
        request = {
            "task_id": task_id,
            "command": command.value,
            "reason": reason,
            "expected_version": expected_version,
        }

        async def mutation(connection: AsyncConnection) -> JsonDict:
            row = await self._task_for_update(connection, task_id)
            await self._insert_audit(
                connection,
                principal=principal,
                action=f"workflow.command.{command.value.lower()}",
                resource_type="WorkflowTask",
                resource_id=task_id,
                space_id=row["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"reason": reason, "duplicate": duplicate},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.workflow.command.accepted.v1",
                aggregate_type="WorkflowTask",
                aggregate_id=task_id,
                aggregate_version=row["version"],
                space_id=row["space_id"],
                trace_id=trace_id,
                payload={
                    "task_id": task_id,
                    "workflow_id": row["workflow_id"],
                    "workflow_type": row["workflow_type"],
                    "status": row["status"],
                    "change": f"COMMAND_{command.value}",
                    "run_id": row["temporal_run_id"],
                    "projection_revision": row["projection_revision"],
                },
            )
            return {
                "id": str(task_id),
                "task": _task_value(row),
                "command_id": idempotency_key,
                "duplicate": duplicate,
            }

        return await self._idempotent(
            principal=principal,
            operation=f"workflow.command:{task_id}:{command.value}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def get_workflow_command_result(
        self,
        *,
        principal: Principal,
        task_id: UUID,
        command: WorkflowCommand,
        reason: str,
        expected_version: int,
        idempotency_key: str,
    ) -> JsonDict | None:
        request_hash = canonical_request_hash(
            {
                "task_id": task_id,
                "command": command.value,
                "reason": reason,
                "expected_version": expected_version,
            }
        )
        async with self._database.engine.connect() as connection:
            existing = (
                (
                    await connection.execute(
                        text(
                            "SELECT request_hash, response_body FROM idempotency_records "
                            "WHERE tenant_id = :tenant AND actor_id = :actor "
                            "AND operation = :operation AND idempotency_key = :key"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "actor": principal.actor_id,
                            "operation": f"workflow.command:{task_id}:{command.value}",
                            "key": idempotency_key,
                        },
                    )
                )
                .mappings()
                .first()
            )
        if existing is None:
            return None
        if existing["request_hash"] != request_hash:
            raise ApiProblem(
                409,
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency key reused",
                "The key was already used with a different request.",
            )
        return dict(existing["response_body"])

    async def apply_projection_event(self, payload: Mapping[str, Any]) -> JsonDict:
        task_id = UUID(str(payload["task_id"]))
        async with self._database.engine.begin() as connection:
            row = await self._task_for_update(connection, task_id)
            event_key = str(payload["event_key"])
            if await self._workflow_event_exists(connection, task_id, event_key):
                return _task_value(row)
            now = datetime.now(UTC)
            status = WorkflowTaskStatus(str(payload["status"]))
            step_key = payload.get("step_key")
            progress = int(payload.get("progress", row["progress"]))
            result = payload.get("result_summary", row["result_summary"])
            await connection.execute(
                text(
                    "UPDATE workflow_tasks SET status = :status, progress = :progress, "
                    "current_step = :step, result_summary = CAST(:result AS jsonb), "
                    "error_code = :error_code, error_detail = :error_detail, "
                    "projection_revision = projection_revision + 1, projection_in_sync = true, "
                    "version = version + 1, updated_at = :now, updated_by = :actor WHERE id = :id"
                ),
                {
                    "status": status.value,
                    "progress": progress,
                    "step": step_key,
                    "result": json.dumps(result, default=str),
                    "error_code": payload.get("error_code"),
                    "error_detail": payload.get("error_detail"),
                    "now": now,
                    "actor": UUID(str(payload["actor_id"])),
                    "id": task_id,
                },
            )
            if step_key:
                await connection.execute(
                    text(
                        "UPDATE workflow_steps SET status = :step_status, attempt = :attempt, "
                        "message = :message, error_code = :error_code, "
                        "started_at = CASE WHEN :is_running "
                        "THEN COALESCE(started_at, :now) ELSE started_at END, "
                        "completed_at = CASE WHEN :is_terminal THEN :now "
                        "ELSE completed_at END, updated_at = :now "
                        "WHERE task_id = :task AND step_key = :step"
                    ),
                    {
                        "step_status": payload.get("step_status", "RUNNING"),
                        "is_running": payload.get("step_status", "RUNNING") == "RUNNING",
                        "is_terminal": payload.get("step_status")
                        in {"SUCCEEDED", "FAILED", "CANCELLED", "COMPENSATED"},
                        "attempt": int(payload.get("attempt", 0)),
                        "message": str(payload.get("message", "")),
                        "error_code": payload.get("error_code"),
                        "now": now,
                        "task": task_id,
                        "step": step_key,
                    },
                )
            await self._append_workflow_event(
                connection,
                task_id=task_id,
                tenant_id=row["tenant_id"],
                space_id=row["space_id"],
                event_key=event_key,
                event_type=str(payload["event_type"]),
                status=status,
                step_key=str(step_key) if step_key else None,
                message=str(payload.get("message", "")),
                details=dict(payload.get("details", {})),
                occurred_at=now,
            )
            next_revision = int(row["projection_revision"]) + 1
            await connection.execute(
                text(
                    "INSERT INTO outbox_events "
                    "(id, tenant_id, space_id, event_type, schema_version, aggregate_type, "
                    "aggregate_id, aggregate_version, correlation_id, trace_id, payload) VALUES "
                    "(:id, :tenant, :space, 'io.nexweave.workflow.task.status-changed.v1', "
                    "'1.0', 'WorkflowTask', :task, :version, :correlation, :trace, "
                    "CAST(:payload AS jsonb))"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": row["tenant_id"],
                    "space": row["space_id"],
                    "task": task_id,
                    "version": int(row["version"]) + 1,
                    "correlation": new_uuid7(),
                    "trace": payload.get("trace_id"),
                    "payload": json.dumps(
                        {
                            "task_id": str(task_id),
                            "workflow_id": row["workflow_id"],
                            "workflow_type": row["workflow_type"],
                            "status": status.value,
                            "change": str(payload["event_type"]),
                            "run_id": payload.get("run_id"),
                            "projection_revision": next_revision,
                        }
                    ),
                },
            )
        return await self.get_workflow_task(task_id)

    async def reconcile_workflow_task(
        self,
        *,
        principal: Principal,
        task_id: UUID,
        temporal_state: Mapping[str, Any],
        trace_id: str,
    ) -> tuple[JsonDict, bool]:
        async with self._database.engine.begin() as connection:
            row = await self._task_for_update(connection, task_id)
            temporal_status = WorkflowTaskStatus(str(temporal_state["status"]))
            run_id = str(temporal_state.get("run_id") or row["temporal_run_id"] or "") or None
            repaired = row["status"] != temporal_status.value or row["temporal_run_id"] != run_id
            now = datetime.now(UTC)
            if repaired:
                await connection.execute(
                    text(
                        "UPDATE workflow_tasks SET status = :status, temporal_run_id = :run, "
                        "projection_revision = projection_revision + 1, projection_in_sync = true, "
                        "last_reconciled_at = :now, version = version + 1, updated_at = :now, "
                        "updated_by = :actor WHERE id = :id"
                    ),
                    {
                        "status": temporal_status.value,
                        "run": run_id,
                        "now": now,
                        "actor": principal.actor_id,
                        "id": task_id,
                    },
                )
                await self._append_workflow_event(
                    connection,
                    task_id=task_id,
                    tenant_id=row["tenant_id"],
                    space_id=row["space_id"],
                    event_key=f"reconcile:{row['projection_revision'] + 1}",
                    event_type="PROJECTION_RECONCILED",
                    status=temporal_status,
                    step_key=None,
                    message="Projection repaired from Temporal authoritative state",
                    details={"previous_status": row["status"], "run_id": run_id},
                    occurred_at=now,
                )
            else:
                await connection.execute(
                    text(
                        "UPDATE workflow_tasks SET projection_in_sync = true, "
                        "last_reconciled_at = :now, updated_at = :now, updated_by = :actor "
                        "WHERE id = :id"
                    ),
                    {"now": now, "actor": principal.actor_id, "id": task_id},
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="workflow.reconcile",
                resource_type="WorkflowTask",
                resource_id=task_id,
                space_id=row["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"repaired": repaired, "temporal_status": temporal_status.value},
            )
            if repaired:
                await self._insert_outbox(
                    connection,
                    principal=principal,
                    event_type="io.nexweave.workflow.task.status-changed.v1",
                    aggregate_type="WorkflowTask",
                    aggregate_id=task_id,
                    aggregate_version=int(row["version"]) + 1,
                    space_id=row["space_id"],
                    trace_id=trace_id,
                    payload={
                        "task_id": task_id,
                        "workflow_id": row["workflow_id"],
                        "workflow_type": row["workflow_type"],
                        "status": temporal_status.value,
                        "change": "PROJECTION_RECONCILED",
                        "run_id": run_id,
                        "projection_revision": int(row["projection_revision"]) + 1,
                    },
                )
        return await self.get_workflow_task(task_id), repaired

    async def workflow_retry_payload(self, task_id: UUID, trace_id: str) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, space_id, workflow_type, workflow_id, "
                            "input_refs, start_paused, created_by FROM workflow_tasks WHERE id = :id"
                        ),
                        {"id": task_id},
                    )
                )
                .mappings()
                .one()
            )
        return _json_value(
            {
                "task_id": row["id"],
                "tenant_id": row["tenant_id"],
                "space_id": row["space_id"],
                "workflow_type": row["workflow_type"],
                "workflow_id": row["workflow_id"],
                "input_refs": row["input_refs"],
                "start_paused": row["start_paused"],
                "actor_id": row["created_by"],
                "trace_id": trace_id,
            }
        )

    async def _task_for_update(self, connection: AsyncConnection, task_id: UUID) -> Any:
        row = (
            (
                await connection.execute(
                    text(
                        f"SELECT {TASK_COLUMNS}, start_paused FROM workflow_tasks "  # noqa: S608
                        "WHERE id = :id FOR UPDATE"
                    ),
                    {"id": task_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Task not found", "The workflow task is unavailable."
            )
        return row

    @staticmethod
    async def _workflow_event_exists(
        connection: AsyncConnection, task_id: UUID, event_key: str
    ) -> bool:
        return (
            await connection.execute(
                text(
                    "SELECT 1 FROM workflow_task_events WHERE task_id = :task AND event_key = :key"
                ),
                {"task": task_id, "key": event_key},
            )
        ).scalar_one_or_none() is not None

    @staticmethod
    async def _append_workflow_event(
        connection: AsyncConnection,
        *,
        task_id: UUID,
        tenant_id: UUID,
        space_id: UUID,
        event_key: str,
        event_type: str,
        status: WorkflowTaskStatus,
        step_key: str | None,
        message: str,
        details: Mapping[str, Any],
        occurred_at: datetime,
    ) -> None:
        await connection.execute(
            text(
                "INSERT INTO workflow_task_events "
                "(id, tenant_id, space_id, task_id, event_key, event_type, workflow_status, "
                "step_key, message, details, occurred_at) VALUES "
                "(:id, :tenant, :space, :task, :key, :event_type, :status, :step, :message, "
                "CAST(:details AS jsonb), :occurred_at)"
            ),
            {
                "id": new_uuid7(),
                "tenant": tenant_id,
                "space": space_id,
                "task": task_id,
                "key": event_key,
                "event_type": event_type,
                "status": status.value,
                "step": step_key,
                "message": message,
                "details": json.dumps(details, default=str),
                "occurred_at": occurred_at,
            },
        )


def _task_value(row: Any) -> JsonDict:
    return _json_value({key.strip(): row[key.strip()] for key in TASK_COLUMNS.split(",")})
