from __future__ import annotations

import pytest

from nexweave_domain import (
    CompileLock,
    CompileMode,
    CompileRuleViolation,
    DataClassification,
    LockedSource,
    compile_input_fingerprint,
    local_structured_compile,
    merge_recompiled_page,
)


def _lock(*sources: LockedSource, external: bool = False) -> CompileLock:
    return CompileLock(
        "schema-v1",
        "PUBLISHED",
        "sha256:" + "a" * 64,
        "prompt-v1",
        "ACTIVE",
        "model-v1",
        "ACTIVE",
        external,
        DataClassification.HIGHLY_RESTRICTED,
        tuple(sources),
        CompileMode.FULL,
    )


def _source(source_id: str, classification: DataClassification) -> LockedSource:
    return LockedSource(source_id, "sha256:" + "b" * 64, f"parse-{source_id}", classification)


def test_compile_lock_fingerprint_is_order_invariant_and_schema_must_be_published() -> None:
    first = _source("source-a", DataClassification.INTERNAL)
    second = _source("source-b", DataClassification.CONFIDENTIAL)

    assert compile_input_fingerprint(_lock(first, second)) == compile_input_fingerprint(
        _lock(second, first)
    )
    unpublished = _lock(first)
    unpublished = CompileLock(
        unpublished.schema_version_id,
        "DRAFT",
        unpublished.composition_checksum,
        unpublished.prompt_version_id,
        unpublished.prompt_status,
        unpublished.model_profile_id,
        unpublished.model_status,
        unpublished.model_externally_hosted,
        unpublished.model_maximum_classification,
        unpublished.sources,
        unpublished.mode,
    )
    with pytest.raises(CompileRuleViolation, match="PUBLISHED") as exc:
        compile_input_fingerprint(unpublished)
    assert exc.value.code == "COMPILE_SCHEMA_NOT_PUBLISHED"


def test_external_model_cannot_receive_highly_restricted_source() -> None:
    with pytest.raises(CompileRuleViolation) as exc:
        compile_input_fingerprint(
            _lock(_source("source-a", DataClassification.HIGHLY_RESTRICTED), external=True)
        )
    assert exc.value.code == "MODEL_EGRESS_DENIED"


def test_local_compile_uses_schema_stable_keys_and_deduplicates_entities() -> None:
    snapshot = {
        "types": [{"key": "nexweave.io/Equipment", "abstract": False}],
        "properties": [{"key": "nexweave.io/description", "typeKey": "nexweave.io/Equipment"}],
        "terms": [{"term": "pump", "targetKey": "nexweave.io/Equipment"}],
        "relations": [],
    }
    segments = [
        {"id": "segment-a", "normalized_text": "Pump A. Operational", "anchor_id": "anchor-a"},
        {"id": "segment-b", "normalized_text": "Pump A. Operational", "anchor_id": "anchor-b"},
    ]

    output = local_structured_compile(schema_snapshot=snapshot, segments=segments)

    assert len(output.entities) == 1
    assert output.entities[0].type_key == "nexweave.io/Equipment"
    assert output.claims[0].predicate_key == "nexweave.io/description"
    assert output.entities[0].anchor_id == "anchor-a"


def test_recompile_preserves_human_protected_sections() -> None:
    generated, protected = merge_recompiled_page(
        generated_sections={"summary": "new model text"},
        existing_protected_sections={"operator-notes": "keep me"},
        ai_generated=True,
    )
    assert generated == {"summary": "new model text"}
    assert protected == {"operator-notes": "keep me"}

    with pytest.raises(CompileRuleViolation) as exc:
        merge_recompiled_page(
            generated_sections=generated,
            existing_protected_sections=protected,
            requested_protected_sections={"operator-notes": "model overwrite"},
            ai_generated=True,
        )
    assert exc.value.code == "WIKI_PROTECTED_SECTION_DENIED"
