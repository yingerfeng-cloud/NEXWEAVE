from __future__ import annotations

from uuid import uuid4

import pytest

from nexweave_domain import (
    ReleaseGate,
    ReleaseRuleViolation,
    reciprocal_rank_fusion,
    release_manifest_checksum,
    validate_release_approver,
    validate_release_gate,
    validate_release_version,
)


def test_release_version_manifest_and_gate_are_deterministic() -> None:
    assert validate_release_version("1.2.3-canary.1") == "1.2.3-canary.1"
    assert release_manifest_checksum({"b": 2, "a": 1}) == release_manifest_checksum(
        {"a": 1, "b": 2}
    )
    validate_release_gate(ReleaseGate(100, 100, 0, 0, True))
    with pytest.raises(ReleaseRuleViolation) as exc:
        validate_release_gate(ReleaseGate(99, 100, 0, 0, True))
    assert exc.value.code == "RELEASE_TRACEABILITY_GATE_FAILED"


def test_release_approval_requires_independence() -> None:
    creator = uuid4()
    with pytest.raises(ReleaseRuleViolation) as exc:
        validate_release_approver(creator_id=creator, approver_id=creator)
    assert exc.value.code == "RELEASE_DUTY_SEPARATION"


def test_rrf_is_explainable_and_not_confidence() -> None:
    fused = reciprocal_rank_fusion({"keyword": ["a", "b"], "semantic": ["b", "c"]}, constant=60)
    assert fused[0][0] == "b"
    assert fused[0][2] == {"keyword": 2, "semantic": 1}
