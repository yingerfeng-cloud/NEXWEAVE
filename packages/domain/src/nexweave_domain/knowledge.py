"""Pure M5 compile and Wiki invariants without framework or provider dependencies."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any

from nexweave_domain.states import DataClassification


class CompileRuleViolation(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


class CompileJobStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"
    CANCELED = "CANCELED"


class CompileMode(StrEnum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    SOURCE_SCOPED = "SOURCE_SCOPED"
    RECOMPILE = "RECOMPILE"


@dataclass(frozen=True, slots=True)
class LockedSource:
    source_version_id: str
    checksum: str
    parse_job_id: str
    classification: DataClassification


@dataclass(frozen=True, slots=True)
class CompileLock:
    schema_version_id: str
    schema_status: str
    composition_checksum: str
    prompt_version_id: str
    prompt_status: str
    model_profile_id: str
    model_status: str
    model_externally_hosted: bool
    model_maximum_classification: DataClassification
    sources: tuple[LockedSource, ...]
    mode: CompileMode
    normalization_version: str = "nexweave.normalize/1"


@dataclass(frozen=True, slots=True)
class CandidateEntity:
    type_key: str
    normalized_key: str
    display_name: str
    attributes: Mapping[str, Any]
    aliases: tuple[str, ...]
    segment_id: str
    anchor_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateClaim:
    entity_key: str
    predicate_key: str
    statement: str
    object_value: Mapping[str, Any]
    segment_id: str
    anchor_id: str | None


@dataclass(frozen=True, slots=True)
class CandidateRelation:
    relation_type_key: str
    source_entity_key: str
    target_entity_key: str
    segment_id: str
    anchor_id: str | None


@dataclass(frozen=True, slots=True)
class SemanticProposal:
    proposal_kind: str
    term: str
    candidate_key: str | None
    proposal: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class StructuredCompileOutput:
    entities: tuple[CandidateEntity, ...]
    claims: tuple[CandidateClaim, ...]
    relations: tuple[CandidateRelation, ...]
    semantic_proposals: tuple[SemanticProposal, ...]


def validate_compile_lock(lock: CompileLock) -> None:
    if lock.schema_status != "PUBLISHED":
        raise CompileRuleViolation(
            "COMPILE_SCHEMA_NOT_PUBLISHED", "Compile requires a PUBLISHED SchemaVersion."
        )
    if lock.prompt_status not in {"ACTIVE", "DRAFT"}:
        raise CompileRuleViolation(
            "COMPILE_PROMPT_UNAVAILABLE", "PromptVersion is unavailable for compilation."
        )
    if lock.model_status not in {"ACTIVE", "DRAFT"}:
        raise CompileRuleViolation(
            "COMPILE_MODEL_UNAVAILABLE", "ModelProfile is unavailable for compilation."
        )
    if not lock.sources:
        raise CompileRuleViolation("COMPILE_SOURCE_REQUIRED", "At least one source is required.")
    highest = max(_classification_level(source.classification) for source in lock.sources)
    if highest > _classification_level(lock.model_maximum_classification):
        raise CompileRuleViolation(
            "MODEL_CLASSIFICATION_DENIED", "The ModelProfile classification ceiling is too low."
        )
    if lock.model_externally_hosted and any(
        source.classification is DataClassification.HIGHLY_RESTRICTED for source in lock.sources
    ):
        raise CompileRuleViolation(
            "MODEL_EGRESS_DENIED", "Highly restricted source data cannot leave the platform."
        )


def compile_input_fingerprint(lock: CompileLock) -> str:
    validate_compile_lock(lock)
    fields = [
        lock.schema_version_id,
        lock.composition_checksum,
        lock.prompt_version_id,
        lock.model_profile_id,
        lock.mode.value,
        lock.normalization_version,
    ]
    fields.extend(
        f"{source.source_version_id}:{source.checksum}:{source.parse_job_id}"
        for source in sorted(lock.sources, key=lambda value: value.source_version_id)
    )
    return "sha256:" + sha256("\n".join(fields).encode()).hexdigest()


def normalize_entity_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", "-", normalized, flags=re.UNICODE)
    normalized = normalized.strip("-")
    if not normalized:
        raise CompileRuleViolation("ENTITY_IDENTITY_EMPTY", "Entity identity is empty.")
    digest = sha256(normalized.encode()).hexdigest()[:12]
    return f"{normalized[:180]}-{digest}"


def render_wiki_markdown(
    *, title: str, generated_sections: Mapping[str, str], protected_sections: Mapping[str, str]
) -> str:
    sections = [f"# {title}"]
    for key, value in sorted(generated_sections.items()):
        sections.extend((f"\n## {key}", value.strip()))
    for key, value in sorted(protected_sections.items()):
        sections.extend((f"\n## {key}", value.strip()))
    return "\n".join(sections).strip() + "\n"


def merge_recompiled_page(
    *,
    generated_sections: Mapping[str, str],
    existing_protected_sections: Mapping[str, str],
    requested_protected_sections: Mapping[str, str] | None = None,
    ai_generated: bool,
) -> tuple[dict[str, str], dict[str, str]]:
    if ai_generated and requested_protected_sections not in (None, existing_protected_sections):
        raise CompileRuleViolation(
            "WIKI_PROTECTED_SECTION_DENIED", "AI cannot modify protected Wiki sections."
        )
    protected = (
        dict(existing_protected_sections)
        if ai_generated
        else dict(requested_protected_sections or existing_protected_sections)
    )
    return dict(generated_sections), protected


def local_structured_compile(
    *, schema_snapshot: Mapping[str, Any], segments: Sequence[Mapping[str, Any]]
) -> StructuredCompileOutput:
    """Replayable local provider; it is deliberately not represented as an external LLM."""

    types = [item for item in schema_snapshot.get("types", []) if not item.get("abstract", False)]
    if not types:
        raise CompileRuleViolation("COMPILE_SCHEMA_EMPTY", "Schema has no concrete entity type.")
    type_keys = {str(item["key"]) for item in types}
    terms: dict[str, list[str]] = {key: [] for key in type_keys}
    for item in schema_snapshot.get("terms", []):
        target_key = str(item.get("targetKey", ""))
        if target_key in terms:
            terms[target_key].append(str(item.get("term", "")))
    properties: dict[str, list[str]] = {key: [] for key in type_keys}
    for item in schema_snapshot.get("properties", []):
        owner = str(item.get("typeKey", ""))
        if owner in properties:
            properties[owner].append(str(item["key"]))
    default_type = str(types[0]["key"])

    entities: list[CandidateEntity] = []
    claims: list[CandidateClaim] = []
    seen: set[str] = set()
    for segment in segments:
        text = str(segment.get("normalized_text") or "").strip()
        if not text:
            continue
        chosen = _match_type(text, terms) or default_type
        display = _candidate_display_name(text)
        normalized = normalize_entity_key(display)
        entity_key = f"{chosen}:{normalized}"
        if entity_key in seen:
            continue
        seen.add(entity_key)
        anchor_id = str(segment["anchor_id"]) if segment.get("anchor_id") else None
        segment_id = str(segment["id"])
        entity = CandidateEntity(
            chosen,
            normalized,
            display,
            {"source_excerpt": text[:1000]},
            (),
            segment_id,
            anchor_id,
        )
        entities.append(entity)
        if properties[chosen]:
            claims.append(
                CandidateClaim(
                    entity_key,
                    sorted(properties[chosen])[0],
                    text[:2000],
                    {"text": text[:2000]},
                    segment_id,
                    anchor_id,
                )
            )

    relations: list[CandidateRelation] = []
    by_type: dict[str, list[CandidateEntity]] = {}
    for entity in entities:
        by_type.setdefault(entity.type_key, []).append(entity)
    for relation in schema_snapshot.get("relations", []):
        sources = by_type.get(str(relation.get("domain", "")), [])
        targets = by_type.get(str(relation.get("range", "")), [])
        if not sources or not targets:
            continue
        source_entity, target_entity = sources[0], targets[-1]
        if (
            source_entity.type_key == target_entity.type_key
            and source_entity.normalized_key == target_entity.normalized_key
        ):
            continue
        relations.append(
            CandidateRelation(
                str(relation["key"]),
                f"{source_entity.type_key}:{source_entity.normalized_key}",
                f"{target_entity.type_key}:{target_entity.normalized_key}",
                source_entity.segment_id,
                source_entity.anchor_id,
            )
        )
    return StructuredCompileOutput(tuple(entities), tuple(claims), tuple(relations), ())


def _match_type(text: str, terms: Mapping[str, Sequence[str]]) -> str | None:
    folded = text.casefold()
    matches = [
        (len(term), key)
        for key, values in terms.items()
        for term in values
        if term and term.casefold() in folded
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0], item[1]))
    return matches[0][1]


def _candidate_display_name(text: str) -> str:
    first = text.splitlines()[0].lstrip("#*- ").strip()
    first = re.split(r"[。！？.!?;；]", first, maxsplit=1)[0].strip()
    return (first or text[:120])[:512]


def _classification_level(value: DataClassification) -> int:
    return {
        DataClassification.PUBLIC: 0,
        DataClassification.INTERNAL: 1,
        DataClassification.CONFIDENTIAL: 2,
        DataClassification.HIGHLY_RESTRICTED: 3,
    }[value]
