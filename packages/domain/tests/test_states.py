from nexweave_domain import DataClassification, ReleaseState


def test_frozen_state_values_are_stable_strings() -> None:
    assert DataClassification.HIGHLY_RESTRICTED == "HIGHLY_RESTRICTED"
    assert ReleaseState.PUBLISHED == "PUBLISHED"
