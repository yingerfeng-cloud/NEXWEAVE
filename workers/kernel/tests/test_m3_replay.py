from __future__ import annotations

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
    SourceIngestionV2Workflow,
    SourceIngestionWorkflow,
)


@activity.defn(name="record_projection_transition")
async def record_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@activity.defn(name="execute_m2_kernel_step")
async def execute_m2_step(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "attempt": 1, "kernel_outcome": "STUB_SUCCEEDED"}


@activity.defn(name="m3_source_verify_raw")
async def verify_raw(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "verified": True}


@activity.defn(name="m3_source_scan_raw")
async def scan_raw(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "scan_status": "CLEAN"}


@activity.defn(name="m3_source_parse_and_persist")
async def parse_and_persist(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "status": "SUCCEEDED",
        "result_checksum": "sha256:" + "a" * 64,
        "segment_count": 1,
        "failure_count": 0,
    }


@pytest.mark.integration
async def test_v1_and_v2_histories_replay_together() -> None:
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
    task_queue = f"m3-replay-{uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SourceIngestionWorkflow, SourceIngestionV2Workflow],
        activities=[record_projection, execute_m2_step, verify_raw, scan_raw, parse_and_persist],
    ):
        v1 = await client.start_workflow(
            SourceIngestionWorkflow.run,
            {
                "task_id": str(uuid4()),
                "actor_id": str(uuid4()),
                "trace_id": "a" * 32,
                "workflow_type": "SOURCE_INGESTION",
                "activity_task_queue": task_queue,
            },
            id=f"source-ingestion-v1-replay/{uuid4()}",
            task_queue=task_queue,
        )
        assert (await v1.result())["kernel_outcome"] == "STUB_SUCCEEDED"
        v2 = await client.start_workflow(
            SourceIngestionV2Workflow.run,
            {
                "parse_job_id": str(uuid4()),
                "trace_id": "b" * 32,
                "workflow_type": "SOURCE_INGESTION_V2",
                "activity_task_queue": task_queue,
            },
            id=f"source-ingestion-v2-replay/{uuid4()}",
            task_queue=task_queue,
        )
        assert (await v2.result())["status"] == "SUCCEEDED"
        histories = [await v1.fetch_history(), await v2.fetch_history()]

    for history in histories:
        replay = await Replayer(workflows=WORKFLOW_CLASSES).replay_workflow(history)
        assert replay.replay_failure is None
