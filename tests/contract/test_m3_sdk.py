import httpx
import pytest

from nexweave_contracts import SourceInvalidationCreate, SourceUploadComplete
from nexweave_sdk import NexweaveClient

ID = "0198d2d3-6c04-7000-8000-000000000011"
TENANT = "0198d2d3-6c04-7000-8000-000000000012"
SPACE = "0198d2d3-6c04-7000-8000-000000000013"
VERSION = "0198d2d3-6c04-7000-8000-000000000014"
ACTOR = "0198d2d3-6c04-7000-8000-000000000015"


@pytest.mark.asyncio
async def test_python_sdk_carries_m3_idempotency_etag_and_async_ids() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path.endswith("/complete"):
            return httpx.Response(
                202,
                json={
                    "source_id": ID,
                    "source_version_id": VERSION,
                    "parse_job_id": ACTOR,
                    "workflow_id": f"source-ingestion/{TENANT}/{ACTOR}",
                    "run_id": "run-1",
                    "duplicate_source_version_ids": [],
                    "source_status": "ACTIVE",
                    "version_status": "PARSING",
                },
            )
        return httpx.Response(
            201,
            json={
                "id": ID,
                "tenant_id": TENANT,
                "space_id": SPACE,
                "source_version_id": VERSION,
                "reason_code": "POLICY_WITHDRAWAL",
                "reason": "Synthetic contract test",
                "policy_version": "m3-v1",
                "created_at": "2026-08-26T00:00:00Z",
                "created_by": ACTOR,
            },
        )

    async with NexweaveClient(
        "https://nexweave.example", "test-token", transport=httpx.MockTransport(handler)
    ) as client:
        completed = await client.complete_source_upload(
            ID,
            SourceUploadComplete(checksum="sha256:" + "a" * 64, size=12),
            idempotency_key="complete-key",
        )
        invalidated = await client.invalidate_source_version(
            VERSION,
            SourceInvalidationCreate(
                reason_code="POLICY_WITHDRAWAL",
                reason="Synthetic contract test",
                policy_version="m3-v1",
            ),
            version=3,
            idempotency_key="invalidate-key",
        )

    assert completed.run_id == "run-1"
    assert str(invalidated.source_version_id) == VERSION
    assert captured[0].headers["idempotency-key"] == "complete-key"
    assert captured[1].headers["idempotency-key"] == "invalidate-key"
    assert captured[1].headers["if-match"] == '"v3"'
    assert all(request.headers["authorization"] == "Bearer test-token" for request in captured)


def test_python_sdk_exposes_all_m3_source_operations() -> None:
    expected: set[str] = {
        "create_source_import_batch",
        "get_source_import_batch",
        "create_source_upload",
        "upload_source_content",
        "complete_source_upload",
        "list_sources",
        "get_source",
        "archive_source",
        "get_source_version",
        "download_source_version",
        "reparse_source_version",
        "retry_parse_job",
        "get_parse_job",
        "list_source_segments",
        "preview_source_version",
        "invalidate_source_version",
    }

    assert expected.issubset(
        {name for name, value in vars(NexweaveClient).items() if callable(value)}
    )
