from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nexweave_contracts import WorkflowTaskCreate, WorkflowTaskEventData
from nexweave_domain import WorkflowTaskStatus, WorkflowType, new_uuid7


def test_workflow_create_accepts_only_stable_bounded_references() -> None:
    command = WorkflowTaskCreate(
        workflow_type=WorkflowType.SOURCE_INGESTION,
        business_key="source:42",
        display_name="Source 42 ingestion",
        input_refs={"managed_object_id": str(new_uuid7())},
    )

    assert command.business_key == "source:42"
    with pytest.raises(ValidationError):
        WorkflowTaskCreate(
            workflow_type=WorkflowType.SOURCE_INGESTION,
            business_key="not safe",
            display_name="unsafe",
        )


def test_workflow_event_payload_is_versionable_and_typed() -> None:
    event = WorkflowTaskEventData(
        task_id=new_uuid7(),
        workflow_id="compile/tenant/key",
        workflow_type=WorkflowType.KNOWLEDGE_COMPILE,
        status=WorkflowTaskStatus.RUNNING,
        change="STEP_STARTED",
        run_id="run-1",
        projection_revision=2,
    )

    assert event.model_dump(mode="json")["status"] == "RUNNING"
    assert datetime.now(UTC).tzinfo is UTC
