from __future__ import annotations

from uuid import uuid4

import pytest

from nexweave_domain import (
    ReviewPolicy,
    ReviewRuleViolation,
    ReviewStage,
    RiskLevel,
    validate_evidence_gate,
    validate_final_approval_separation,
    validate_review_policy,
)


def test_high_risk_review_requires_three_independent_stages() -> None:
    valid = ReviewPolicy(
        RiskLevel.HIGH,
        (ReviewStage.ENGINEERING, ReviewStage.EXPERT, ReviewStage.APPROVAL),
        False,
        1,
    )
    validate_review_policy(valid)
    with pytest.raises(ReviewRuleViolation) as exc:
        validate_review_policy(
            ReviewPolicy(RiskLevel.HIGH, (ReviewStage.ENGINEERING, ReviewStage.APPROVAL), False, 1)
        )
    assert exc.value.code == "REVIEW_POLICY_HIGH_RISK_SEPARATION"


def test_only_low_risk_policy_can_batch_and_final_approver_is_separate() -> None:
    with pytest.raises(ReviewRuleViolation) as exc:
        validate_review_policy(
            ReviewPolicy(
                RiskLevel.MEDIUM,
                (ReviewStage.ENGINEERING, ReviewStage.EXPERT),
                True,
                2,
            )
        )
    assert exc.value.code == "REVIEW_POLICY_BATCH_DENIED"

    creator = uuid4()
    with pytest.raises(ReviewRuleViolation) as exc:
        validate_final_approval_separation(
            risk=RiskLevel.HIGH,
            creator_id=creator,
            reviewer_ids=[],
            approver_id=creator,
        )
    assert exc.value.code == "REVIEW_DUTY_SEPARATION"


def test_approval_requires_valid_evidence() -> None:
    with pytest.raises(ReviewRuleViolation) as exc:
        validate_evidence_gate(has_valid_evidence=False)
    assert exc.value.code == "CLAIM_EVIDENCE_REQUIRED"
    validate_evidence_gate(has_valid_evidence=True)
