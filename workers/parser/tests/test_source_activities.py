from typing import Any

import pytest
from temporalio.exceptions import ApplicationError

from nexweave_worker_parser.activities import SourceActivities


class RepositoryStub:
    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

    async def load_parse_context(self, parse_job_id: object) -> dict[str, Any]:
        del parse_job_id
        return self.context


class ScannerMustNotRun:
    async def scan(self, **kwargs: object) -> None:
        del kwargs
        raise AssertionError("scanner must not run for a recorded CLEAN fact")


class DependencyMustNotRun:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"dependency must not run: {name}")


@pytest.mark.asyncio
async def test_scan_activity_replay_uses_recorded_clean_fact() -> None:
    activities = SourceActivities(  # type: ignore[arg-type]
        repository=RepositoryStub({"status": "RUNNING", "malware_scan_status": "CLEAN"}),
        storage=DependencyMustNotRun(),
        scanner=ScannerMustNotRun(),
        parser=DependencyMustNotRun(),
    )

    result = await activities.scan_raw(
        {"parse_job_id": "0198d2d3-6c04-7000-8000-000000000011", "run_id": "run-2"}
    )

    assert result == {
        "parse_job_id": "0198d2d3-6c04-7000-8000-000000000011",
        "scan_status": "CLEAN",
        "duplicate": True,
    }


@pytest.mark.asyncio
async def test_parse_activity_is_fail_closed_until_clamav_clean_fact() -> None:
    activities = SourceActivities(  # type: ignore[arg-type]
        repository=RepositoryStub(
                {
                    "status": "RUNNING",
                    "malware_scan_status": "PENDING",
                "source_document_status": "ACTIVE",
                "source_version_status": "PARSING",
                "invalidated": False,
                "latest_parse_job_id": "0198d2d3-6c04-7000-8000-000000000011",
            }
        ),
        storage=DependencyMustNotRun(),
        scanner=DependencyMustNotRun(),
        parser=DependencyMustNotRun(),
    )

    with pytest.raises(ApplicationError) as error:
        await activities.parse_and_persist(
            {"parse_job_id": "0198d2d3-6c04-7000-8000-000000000011", "run_id": "run-2"}
        )

    assert error.value.type == "SOURCE_SECURITY_POLICY_FAILED"
    assert error.value.non_retryable is True
