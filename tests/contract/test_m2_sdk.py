from typing import Any

import httpx
import pytest

from nexweave_contracts import WorkflowCommandRequest, WorkflowTaskCreate
from nexweave_domain import WorkflowCommand, WorkflowType
from nexweave_sdk import NexweaveClient


def _task() -> dict[str, Any]:
    return {
        "id": "0198d2d3-6c04-7000-8000-000000000011",
        "tenant_id": "0198d2d3-6c04-7000-8000-000000000012",
        "space_id": "0198d2d3-6c04-7000-8000-000000000013",
        "workflow_type": "SOURCE_INGESTION",
        "business_key": "sdk-contract",
        "display_name": "SDK contract",
        "workflow_id": "source-ingestion/tenant/sdk-contract",
        "temporal_run_id": "run-1",
        "status": "PAUSED",
        "version": 2,
        "progress": 0,
        "current_step": None,
        "input_refs": {},
        "result_summary": {},
        "error_code": None,
        "error_detail": None,
        "projection_revision": 2,
        "projection_in_sync": True,
        "last_reconciled_at": None,
        "created_at": "2026-08-24T00:00:00Z",
        "created_by": "0198d2d3-6c04-7000-8000-000000000014",
        "updated_at": "2026-08-24T00:00:01Z",
        "updated_by": "0198d2d3-6c04-7000-8000-000000000014",
    }


@pytest.mark.asyncio
async def test_python_sdk_carries_m2_idempotency_and_etag_contracts() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path.endswith("/commands"):
            return httpx.Response(
                202,
                json={"task": _task(), "command_id": "command-key", "duplicate": False},
            )
        return httpx.Response(202, json=_task())

    space_id = "0198d2d3-6c04-7000-8000-000000000013"
    task_id = "0198d2d3-6c04-7000-8000-000000000011"
    async with NexweaveClient(
        "https://nexweave.example", "test-token", transport=httpx.MockTransport(handler)
    ) as client:
        created = await client.create_workflow_task(
            space_id,
            WorkflowTaskCreate(
                workflow_type=WorkflowType.SOURCE_INGESTION,
                business_key="sdk-contract",
                display_name="SDK contract",
                start_paused=True,
            ),
            idempotency_key="create-key",
        )
        commanded = await client.command_workflow_task(
            task_id,
            WorkflowCommandRequest(action=WorkflowCommand.RESUME, reason="continue"),
            version=2,
            idempotency_key="command-key",
        )

    assert created.workflow_id.endswith("/sdk-contract")
    assert commanded.command_id == "command-key"
    assert captured[0].headers["idempotency-key"] == "create-key"
    assert captured[1].headers["idempotency-key"] == "command-key"
    assert captured[1].headers["if-match"] == '"v2"'
    assert all(request.headers["authorization"] == "Bearer test-token" for request in captured)
