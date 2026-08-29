from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nexweave_contracts import (
    ParseEventData,
    SourceInvalidatedEventData,
    SourceVersionReadyEventData,
    SourceVersionSupersededEventData,
)
from nexweave_domain import DataClassification, new_uuid7


def _context() -> dict[str, object]:
    return {
        "tenant_id": new_uuid7(),
        "space_id": new_uuid7(),
        "source_id": new_uuid7(),
        "source_version_id": new_uuid7(),
        "aggregate_version": 2,
        "correlation_id": new_uuid7(),
        "causation_id": new_uuid7(),
        "trace_id": "a" * 32,
    }


def test_m3_source_event_payloads_are_versioned_reference_only_contracts() -> None:
    context = _context()
    ready = SourceVersionReadyEventData(
        **context,
        status="STORED",
        checksum="sha256:" + "b" * 64,
        classification=DataClassification.INTERNAL,
        parse_job_id=new_uuid7(),
        workflow_id="source-ingestion/tenant/job",
    )
    superseded = SourceVersionSupersededEventData(
        **context,
        old_source_version_id=context["source_version_id"],
        new_source_version_id=new_uuid7(),
        reason="explicit-replacement",
    )
    invalidated = SourceInvalidatedEventData(
        **context,
        status="PARSED",
        reason_code="POLICY_WITHDRAWAL",
        policy_version="m3-v1",
    )

    assert ready.classification is DataClassification.INTERNAL
    assert superseded.old_source_version_id == context["source_version_id"]
    assert invalidated.reason_code == "POLICY_WITHDRAWAL"
    assert all(
        "raw" not in item.model_dump(mode="json") and "download_url" not in item.model_dump()
        for item in (ready, superseded, invalidated)
    )


def test_parse_event_requires_terminal_status_and_safe_reference_fields() -> None:
    event = ParseEventData(
        **_context(),
        parse_job_id=new_uuid7(),
        status="PARTIAL_FAILED",
        parser_id="nexweave.parser.builtin",
        parser_version="1.0.0",
        config_checksum="sha256:" + "c" * 64,
        document_model_version="1.0",
        locator_version="1.0",
        result_checksum="sha256:" + "d" * 64,
        failure_count=1,
        error_code="OCR_REQUIRED",
        workflow_id="source-ingestion/tenant/job",
        run_id="run-1",
    )

    assert event.terminal_status.value == "PARTIAL_FAILED"
    with pytest.raises(ValidationError):
        ParseEventData.model_validate({**event.model_dump(), "status": "RUNNING"})


def test_source_event_trace_id_is_w3c_trace_identifier() -> None:
    context = _context()
    context["trace_id"] = datetime.now(UTC).isoformat()
    with pytest.raises(ValidationError):
        SourceInvalidatedEventData(
            **context,
            status="PARSED",
            reason_code="POLICY_WITHDRAWAL",
            policy_version="m3-v1",
        )
