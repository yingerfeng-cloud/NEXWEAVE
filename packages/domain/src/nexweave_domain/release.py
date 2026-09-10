"""Pure M7 quality, immutable Release and retrieval invariants."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID

from nexweave_domain.semantic import canonical_json


class ReleaseRuleViolation(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


class EvaluationCaseType(StrEnum):
    ANSWERABLE = "ANSWERABLE"
    UNANSWERABLE = "UNANSWERABLE"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    CONFLICT = "CONFLICT"
    MULTI_SOURCE = "MULTI_SOURCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RetrievalStrategy(StrEnum):
    KEYWORD = "KEYWORD"
    ATTRIBUTE = "ATTRIBUTE"
    SEMANTIC = "SEMANTIC"
    HYBRID = "HYBRID"


@dataclass(frozen=True, slots=True)
class ReleaseGate:
    traceability_percent: int
    schema_compliance_percent: int
    blocking_lint_count: int
    unresolved_blocking_conflicts: int
    evaluation_passed: bool


SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def validate_release_version(value: str) -> str:
    if not SEMVER_PATTERN.fullmatch(value):
        raise ReleaseRuleViolation("RELEASE_VERSION_INVALID", "Release version must be SemVer.")
    return value


def release_manifest_checksum(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + sha256(canonical_json(dict(manifest))).hexdigest()


def validate_release_gate(gate: ReleaseGate) -> None:
    if gate.traceability_percent != 100:
        raise ReleaseRuleViolation(
            "RELEASE_TRACEABILITY_GATE_FAILED", "Every released knowledge item must be traceable."
        )
    if gate.schema_compliance_percent != 100:
        raise ReleaseRuleViolation(
            "RELEASE_SCHEMA_GATE_FAILED",
            "Every released knowledge item must match the fixed SchemaVersion.",
        )
    if gate.blocking_lint_count:
        raise ReleaseRuleViolation(
            "RELEASE_LINT_GATE_FAILED",
            "Blocking lint findings must be resolved before publication.",
        )
    if gate.unresolved_blocking_conflicts:
        raise ReleaseRuleViolation(
            "RELEASE_CONFLICT_GATE_FAILED", "Unresolved blocking conflicts prevent publication."
        )
    if not gate.evaluation_passed:
        raise ReleaseRuleViolation(
            "RELEASE_EVALUATION_GATE_FAILED", "The fixed evaluation suite did not pass."
        )


def validate_release_approver(*, creator_id: UUID, approver_id: UUID) -> None:
    if creator_id == approver_id:
        raise ReleaseRuleViolation(
            "RELEASE_DUTY_SEPARATION", "A ReleaseCandidate creator cannot approve publication."
        )


def reciprocal_rank_fusion(
    rankings: Mapping[str, Sequence[str]], *, constant: int = 60
) -> list[tuple[str, float, dict[str, int]]]:
    if constant < 1:
        raise ReleaseRuleViolation("RETRIEVAL_RRF_INVALID", "RRF constant must be positive.")
    scores: dict[str, float] = {}
    positions: dict[str, dict[str, int]] = {}
    for strategy, ordered_ids in sorted(rankings.items()):
        for rank, object_id in enumerate(ordered_ids, start=1):
            scores[object_id] = scores.get(object_id, 0.0) + 1.0 / (constant + rank)
            positions.setdefault(object_id, {})[strategy] = rank
    return sorted(
        ((key, score, positions[key]) for key, score in scores.items()),
        key=lambda item: (-item[1], item[0]),
    )
