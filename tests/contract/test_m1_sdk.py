import json

import httpx
import pytest

from nexweave_sdk import NexweaveClient, NexweaveSdkError


@pytest.mark.asyncio
async def test_python_sdk_applies_auth_trace_and_validates_public_contract() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "0198d2d3-6c04-7000-8000-000000000001",
                        "tenant_id": "0198d2d3-6c04-7000-8000-000000000002",
                        "organization_id": "0198d2d3-6c04-7000-8000-000000000003",
                        "slug": "quality",
                        "display_name": "Quality",
                        "description": "Trusted",
                        "default_classification": "INTERNAL",
                        "status": "ACTIVE",
                        "version": 1,
                        "created_at": "2026-08-24T00:00:00Z",
                        "created_by": "0198d2d3-6c04-7000-8000-000000000004",
                        "updated_at": "2026-08-24T00:00:00Z",
                        "updated_by": "0198d2d3-6c04-7000-8000-000000000004",
                        "archived_at": None,
                    }
                ]
            },
        )

    async with NexweaveClient(
        "https://nexweave.example", "test-token", transport=httpx.MockTransport(handler)
    ) as client:
        spaces = await client.list_spaces()

    assert spaces.items[0].slug == "quality"
    assert captured[0].headers["authorization"] == "Bearer test-token"
    assert captured[0].headers["traceparent"].startswith("00-")


@pytest.mark.asyncio
async def test_python_sdk_maps_problem_details_without_losing_trace() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            content=json.dumps(
                {
                    "code": "ACCESS_DENIED",
                    "detail": "The action is not allowed.",
                    "trace_id": "a" * 32,
                }
            ),
            headers={"Content-Type": "application/problem+json"},
        )

    async with NexweaveClient(
        "https://nexweave.example", "test-token", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(NexweaveSdkError) as captured:
            await client.list_spaces()

    assert captured.value.code == "ACCESS_DENIED"
    assert captured.value.trace_id == "a" * 32
