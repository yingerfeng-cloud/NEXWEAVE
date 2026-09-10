"""M6 framework-free Claim/Evidence, conflict and human-review policy rules."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ReviewRuleViolation(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ReviewStage(StrEnum):
    ENGINEERING = "ENGINEERING"
    EXPERT = "EXPERT"
    APPROVAL = "APPROVAL"


class ReviewDecision(StrEnum):
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    REJECT = "REJECT"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    TRANSFER = "TRANSFER"


class ConflictResolution(StrEnum):
    RETAIN_BOTH = "RETAIN_BOTH"
    CONDITIONAL = "CONDITIONAL"
    MERGE = "MERGE"
    UNRESOLVED = "UNRESOLVED"
    EXPIRED = "EXPIRED"
    REOPEN = "REOPEN"


@dataclass(frozen=True, slots=True)
class ReviewPolicy:
    risk: RiskLevel
    stages: tuple[ReviewStage, ...]
    allow_batch: bool
    batch_limit: int


def validate_review_policy(policy: ReviewPolicy) -> None:
    if not policy.stages or policy.stages[0] is not ReviewStage.ENGINEERING:
        raise ReviewRuleViolation("REVIEW_POLICY_INITIAL_STAGE", "Review starts with engineering.")
    if len(set(policy.stages)) != len(policy.stages):
        raise ReviewRuleViolation("REVIEW_POLICY_STAGE_DUPLICATE", "Review stages must be unique.")
    if policy.risk is RiskLevel.HIGH and policy.stages != (
        ReviewStage.ENGINEERING,
        ReviewStage.EXPERT,
        ReviewStage.APPROVAL,
    ):
        raise ReviewRuleViolation(
            "REVIEW_POLICY_HIGH_RISK_SEPARATION",
            "High risk requires engineering, expert and final approval in that order.",
        )
    if policy.allow_batch and (policy.risk is not RiskLevel.LOW or policy.batch_limit < 2):
        raise ReviewRuleViolation(
            "REVIEW_POLICY_BATCH_DENIED", "Only low-risk policies may allow bounded batch review."
        )
    if policy.batch_limit < 1 or policy.batch_limit > 100:
        raise ReviewRuleViolation(
            "REVIEW_POLICY_BATCH_LIMIT", "Batch limit must be between 1 and 100."
        )


def validate_final_approval_separation(
    *, risk: RiskLevel, creator_id: UUID, reviewer_ids: Iterable[UUID], approver_id: UUID
) -> None:
    if risk is RiskLevel.HIGH and (approver_id == creator_id or approver_id in set(reviewer_ids)):
        raise ReviewRuleViolation(
            "REVIEW_DUTY_SEPARATION", "High-risk final approval must be by an independent person."
        )


def validate_evidence_gate(*, has_valid_evidence: bool, is_causal_relation: bool = False) -> None:
    if not has_valid_evidence:
        code = (
            "CAUSAL_RELATION_EVIDENCE_REQUIRED" if is_causal_relation else "CLAIM_EVIDENCE_REQUIRED"
        )
        raise ReviewRuleViolation(
            code, "Approval requires an accepted Evidence record with a VALID anchor."
        )
