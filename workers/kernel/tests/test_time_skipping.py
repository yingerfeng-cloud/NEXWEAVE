from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nexweave_worker_kernel.workflows import HumanReviewWorkflow


@activity.defn(name="record_projection_transition")
async def record_projection_transition(payload: dict[str, object]) -> dict[str, object]:
    return payload


@activity.defn(name="execute_m2_kernel_step")
async def execute_kernel_step(payload: dict[str, object]) -> dict[str, object]:
    return {**payload, "attempt": 1, "kernel_outcome": "STUB_SUCCEEDED"}


@activity.defn(name="compensate_m2_kernel_step")
async def compensate_kernel_step(payload: dict[str, object]) -> dict[str, object]:
    return {**payload, "kernel_outcome": "STUB_COMPENSATED"}


@pytest.mark.integration
async def test_human_review_timeout_escalates_with_time_skipping() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        task_queue = f"m2-time-skip-{uuid4()}"
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[HumanReviewWorkflow],
            activities=[
                record_projection_transition,
                execute_kernel_step,
                compensate_kernel_step,
            ],
        ):
            handle = await environment.client.start_workflow(
                HumanReviewWorkflow.run,
                {
                    "task_id": str(uuid4()),
                    "actor_id": str(uuid4()),
                    "trace_id": "a" * 32,
                    "workflow_type": "HUMAN_REVIEW",
                    "activity_task_queue": task_queue,
                    "approval_timeout_seconds": 300,
                },
                id=f"human-review/{uuid4()}",
                task_queue=task_queue,
            )
            await environment.sleep(timedelta(seconds=301))
            state = await handle.query(HumanReviewWorkflow.state)
            assert state["approval_escalated"] is True
            await handle.execute_update(
                HumanReviewWorkflow.command,
                {
                    "command_id": str(uuid4()),
                    "action": "APPROVE",
                    "reason": "time-skipping test approval",
                    "actor_id": str(uuid4()),
                },
            )
            assert (await handle.result())["kernel_outcome"] == "STUB_SUCCEEDED"
