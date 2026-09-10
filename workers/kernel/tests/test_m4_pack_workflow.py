from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from nexweave_worker_kernel.workflows import (
    WORKFLOW_CLASSES,
    DomainPackInstallV2Workflow,
    DomainPackInstallWorkflow,
)


@activity.defn(name="record_projection_transition")
async def record_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@activity.defn(name="execute_m2_kernel_step")
async def execute_stub(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "attempt": 1, "kernel_outcome": "STUB_SUCCEEDED"}


@activity.defn(name="m4_pack_resolve_compose_persist")
async def execute_installation(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "status": "ACTIVE",
        "candidate_schema_version_id": str(uuid4()),
    }


@activity.defn(name="m4_pack_fail")
async def fail_installation(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "status": "FAILED"}


@pytest.mark.integration
async def test_pack_v1_stub_and_v2_business_histories_replay_together() -> None:
    endpoint = os.environ.get("NEXWEAVE_TEMPORAL_TEST_ENDPOINT")
    if endpoint:
        client = await Client.connect(
            endpoint,
            namespace=os.environ.get("NEXWEAVE_TEMPORAL_TEST_NAMESPACE", "nexweave-dev"),
        )
        await _exercise_and_replay(client)
        return
    cache = os.environ.get("NEXWEAVE_TEMPORAL_TEST_SERVER_CACHE")
    if cache is not None:
        Path(cache).mkdir(parents=True, exist_ok=True)
    async with await WorkflowEnvironment.start_time_skipping(
        download_dest_dir=cache
    ) as environment:
        await _exercise_and_replay(environment.client)


async def _exercise_and_replay(client: Client) -> None:
    queue = f"m4-pack-replay-{uuid4()}"
    async with Worker(
        client,
        task_queue=queue,
        workflows=[DomainPackInstallWorkflow, DomainPackInstallV2Workflow],
        activities=[
            record_projection,
            execute_stub,
            execute_installation,
            fail_installation,
        ],
    ):
        common = {
            "task_id": str(uuid4()),
            "actor_id": str(uuid4()),
            "trace_id": "a" * 32,
            "workflow_type": "DOMAIN_PACK_INSTALL",
            "activity_task_queue": queue,
        }
        v1 = await client.start_workflow(
            DomainPackInstallWorkflow.run,
            common,
            id=f"pack-v1/{uuid4()}",
            task_queue=queue,
        )
        # The v1 approval gate remains historical and must not be redefined.
        for _ in range(100):
            if (await v1.query(DomainPackInstallWorkflow.state))["status"] == "WAITING":
                break
            await asyncio.sleep(0.01)
        await v1.execute_update(
            DomainPackInstallWorkflow.command,
            {
                "command_id": str(uuid4()),
                "action": "APPROVE",
                "reason": "historical replay fixture",
                "actor_id": str(uuid4()),
            },
        )
        assert (await v1.result())["kernel_outcome"] == "STUB_SUCCEEDED"
        v2 = await client.start_workflow(
            DomainPackInstallV2Workflow.run,
            {**common, "installation_id": str(uuid4())},
            id=f"pack-v2/{uuid4()}",
            task_queue=queue,
        )
        assert (await v2.result())["status"] == "ACTIVE"
        histories = [await v1.fetch_history(), await v2.fetch_history()]

    for history in histories:
        replay = await Replayer(workflows=WORKFLOW_CLASSES).replay_workflow(history)
        assert replay.replay_failure is None
