import pytest
from pydantic import ValidationError

from nexweave_contracts.forecast import ForecastProfile
from nexweave_domain.forecast import validate_temporal_declarations
from nexweave_domain.semantic import SemanticRuleViolation


@pytest.mark.parametrize(
    ("past", "future", "valid"),
    [(8, 0, True), (0, 8, True), (4, 4, True), (8, 1, False), (8, 8, False)],
)
def test_profile_and_binding_share_total_eight_covariate_budget(past, future, valid):
    all_keys = [f"example.io/s{i}" for i in range(17)]
    profile = {
        "key": "example.io/profile",
        "displayName": "Bounded profile",
        "target": all_keys[0],
        "pastCovariates": all_keys[1 : past + 1],
        "futureCovariates": all_keys[past + 1 : past + future + 1],
    }
    schema = {
        "types": [{"key": "example.io/equipment"}],
        "signalDefinitions": [
            {"key": k, "typeKey": "example.io/equipment", "unit": "unit"} for k in all_keys
        ],
        "forecastProfiles": [profile],
    }
    if valid:
        ForecastProfile.model_validate(profile)
        validate_temporal_declarations(schema)
    else:
        with pytest.raises(ValidationError):
            ForecastProfile.model_validate(profile)
        with pytest.raises(SemanticRuleViolation):
            validate_temporal_declarations(schema)
