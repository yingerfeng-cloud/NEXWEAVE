from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexweave_contracts import CompileCompletedEventData, CompileJobCreate
from nexweave_domain import new_uuid7


def test_compile_create_rejects_duplicate_fixed_source_versions() -> None:
    source_id = new_uuid7()
    with pytest.raises(ValidationError, match="must be unique"):
        CompileJobCreate(
            schema_version_id=new_uuid7(),
            source_version_ids=(source_id, source_id),
            prompt_version_id=new_uuid7(),
            model_profile_id=new_uuid7(),
        )


def test_compile_completed_event_has_versionable_output_references() -> None:
    event = CompileCompletedEventData(
        compile_job_id=new_uuid7(),
        schema_version_id=new_uuid7(),
        composition_checksum="sha256:" + "a" * 64,
        prompt_version_id=new_uuid7(),
        model_profile_id=new_uuid7(),
        source_version_ids=(new_uuid7(),),
        output_versions={"entities": (new_uuid7(),), "wiki_pages": (new_uuid7(),)},
        stats={"entity_count": 1, "page_count": 1},
    )

    assert event.stats["page_count"] == 1
    assert set(event.output_versions) == {"entities", "wiki_pages"}
