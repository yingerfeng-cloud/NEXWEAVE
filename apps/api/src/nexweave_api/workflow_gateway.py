"""Temporal client adapter for the M2 reliable-workflow kernel."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from nexweave_api.errors import ApiProblem
from nexweave_api.settings import Settings
from nexweave_application import WorkflowExecutionInfo


class TemporalWorkflowGateway:
    """Keep provider-specific Temporal calls outside domain and application policy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None

    async def connect(self) -> None:
        if self._client is None:
            self._client = await Client.connect(
                self._settings.temporal_endpoint,
                namespace=self._settings.temporal_namespace,
            )

    async def close(self) -> None:
        self._client = None

    async def start(
        self, *, workflow_name: str, workflow_id: str, payload: dict[str, Any]
    ) -> WorkflowExecutionInfo:
        client = await self._connected_client()
        payload = {**payload, "activity_task_queue": self._settings.temporal_activity_task_queue}
        try:
            handle = await client.start_workflow(
                workflow_name,
                payload,
                id=workflow_id,
                task_queue=self._settings.temporal_workflow_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                run_timeout=timedelta(minutes=30),
                task_timeout=timedelta(seconds=10),
                static_summary=f"NEXWEAVE M2 {payload['workflow_type']} kernel task",
            )
            run_id = handle.first_execution_run_id or handle.run_id or ""
            return WorkflowExecutionInfo(workflow_id, run_id, "RUNNING")
        except WorkflowAlreadyStartedError as exc:
            handle = client.get_workflow_handle(workflow_id, run_id=exc.run_id)
            description = await handle.describe()
            return WorkflowExecutionInfo(
                workflow_id,
                description.run_id,
                description.status.name if description.status else "RUNNING",
            )
        except Exception as exc:
            raise _temporal_problem(exc) from exc

    async def command(
        self,
        *,
        workflow_id: str,
        command_id: str,
        action: str,
        reason: str,
        actor_id: str,
    ) -> dict[str, Any]:
        client = await self._connected_client()
        try:
            result = await client.get_workflow_handle(workflow_id).execute_update(
                "command",
                {
                    "command_id": command_id,
                    "action": action,
                    "reason": reason,
                    "actor_id": actor_id,
                },
                id=command_id,
            )
            return dict(result)
        except Exception as exc:
            raise _temporal_problem(exc) from exc

    async def retry(
        self, *, workflow_name: str, workflow_id: str, payload: dict[str, Any]
    ) -> WorkflowExecutionInfo:
        client = await self._connected_client()
        payload = {**payload, "activity_task_queue": self._settings.temporal_activity_task_queue}
        try:
            handle = await client.start_workflow(
                workflow_name,
                payload,
                id=workflow_id,
                task_queue=self._settings.temporal_workflow_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                run_timeout=timedelta(minutes=30),
                task_timeout=timedelta(seconds=10),
                static_summary=f"NEXWEAVE M2 retry {payload['workflow_type']} kernel task",
            )
            return WorkflowExecutionInfo(
                workflow_id,
                handle.first_execution_run_id or handle.run_id or "",
                "RUNNING",
            )
        except Exception as exc:
            raise _temporal_problem(exc) from exc

    async def inspect(self, *, workflow_id: str) -> dict[str, Any]:
        client = await self._connected_client()
        try:
            handle = client.get_workflow_handle(workflow_id)
            description = await handle.describe()
            try:
                state = dict(await handle.query("state"))
            except Exception:
                state = {}
            temporal_status = description.status.name if description.status else "RUNNING"
            return _merge_temporal_state(state, description.run_id, temporal_status)
        except Exception as exc:
            raise _temporal_problem(exc) from exc

    async def _connected_client(self) -> Client:
        await self.connect()
        assert self._client is not None
        return self._client


def _projection_status(temporal_status: str) -> str:
    return {
        "COMPLETED": "SUCCEEDED",
        "CANCELED": "CANCELLED",
        "TERMINATED": "FAILED",
        "FAILED": "FAILED",
        "TIMED_OUT": "TIMED_OUT",
    }.get(temporal_status, "RUNNING")


def _merge_temporal_state(
    workflow_query_state: dict[str, Any], run_id: str, temporal_status: str
) -> dict[str, Any]:
    state = {**workflow_query_state, "run_id": run_id, "temporal_status": temporal_status}
    if temporal_status == "RUNNING":
        state.setdefault("status", "RUNNING")
    else:
        state["status"] = _projection_status(temporal_status)
    return state


def _temporal_problem(exc: Exception) -> ApiProblem:
    return ApiProblem(
        503,
        "WORKFLOW_DEPENDENCY_UNAVAILABLE",
        "Workflow service unavailable",
        "Temporal could not complete the workflow operation safely.",
        extensions={"provider_error": type(exc).__name__},
    )
