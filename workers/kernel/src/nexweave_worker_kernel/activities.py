"""Retryable, observable I/O activities for the M2 Temporal kernel."""

from __future__ import annotations

from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from nexweave_api.workflow_repository import WorkflowRepository


class KernelActivities:
    def __init__(self, repository: WorkflowRepository) -> None:
        self._repository = repository

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
