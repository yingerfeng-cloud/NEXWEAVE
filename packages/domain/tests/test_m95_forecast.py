from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from nexweave_contracts.forecast import ForecastProfile
from nexweave_contracts.semantic import SemanticDeclarations
from nexweave_domain.forecast import (
    build_observation_window,
    interpret_forecast,
    validate_forecast_result,
)
from nexweave_domain.semantic import SemanticRuleViolation, compose_declarations


def fixture():
    profile = {
        "target": "demo.io/temp",
        "pastCovariates": [],
        "futureCovariates": ["demo.io/load"],
        "frequencySeconds": 60,
    }
    binding = {
        "columns": [
            {"signal_key": "demo.io/temp", "column": "t", "unit": "degC"},
            {"signal_key": "demo.io/load", "column": "l", "unit": "%"},
        ],
        "timestamp_column": "timestamp",
        "quality_column": "q",
        "snapshot": {
            "profile": profile,
            "source_checksum": "sha256:x",
            "schema_checksum": "sha256:y",
            "entity": {"display_name": "Demo"},
        },
        "operating_context": "demo",
        "data_kind": "SYNTHETIC",
        "source_version_id": "source",
        "schema_version_id": "schema",
        "entity_id": "entity",
        "created_at": "2026-09-07T00:00:00Z",
    }
    rows = ["timestamp,t,l,q"] + [
        f"{(datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=i)).isoformat()},50,70,GOOD"
        for i in range(40)
    ]
    request = {
        "history_points": 32,
        "horizon": 3,
        "scenario_name": "scenario",
        "future_paths": [{"signal_key": "demo.io/load", "unit": "%", "values": [70, 80, 95]}],
    }
    return "\n".join(rows).encode(), binding, request


def test_cutoff_prevents_target_leakage_and_preserves_provenance():
    raw, b, r = fixture()
    r["cutoff"] = "2026-09-01T00:35:00+00:00"
    c = build_observation_window(raw, b, r)
    assert len(c["observations"]) == 32
    assert c["origin"] == r["cutoff"]
    assert c["prediction_timestamps"][0] == "2026-09-01T00:36:00+00:00"
    assert c["observations"][-1]["source_row"] == 37
    assert c["data_kind"] == "SYNTHETIC"


@pytest.mark.parametrize("change", ["gap", "nan", "quality", "timezone", "duplicate"])
def test_rejects_unsafe_observations(change):
    raw, b, r = fixture()
    if change == "gap":
        raw = raw.replace(b"00:20:00", b"00:20:30")
    if change == "nan":
        raw = raw.replace(b",50,", b",NaN,", 1)
    if change == "quality":
        raw = raw.replace(b"GOOD", b"BAD", 1)
    if change == "timezone":
        raw = raw.replace(b"+00:00", b"")
    if change == "duplicate":
        raw += b"\n" + raw.splitlines()[-1]
    with pytest.raises(SemanticRuleViolation, match="regular"):
        build_observation_window(raw, b, r)


@pytest.mark.parametrize("change", ["missing", "unit", "horizon"])
def test_future_path_validation(change):
    raw, b, r = fixture()
    if change == "missing":
        r["future_paths"] = []
    if change == "unit":
        r["future_paths"][0]["unit"] = "fraction"
    if change == "horizon":
        r["future_paths"][0]["values"] = [70]
    with pytest.raises(SemanticRuleViolation):
        build_observation_window(raw, b, r)


def test_quantiles_and_event_do_not_invent_fault_probability():
    raw, b, r = fixture()
    c = build_observation_window(raw, b, r)
    result = {"quantiles": {"0.1": [48] * 3, "0.5": [50] * 3, "0.9": [54] * 3}}
    validate_forecast_result(result, 3)
    i = interpret_forecast(
        c,
        result,
        {"threshold": 53, "unit": "degC", "label": "attention", "authority": "DEMONSTRATION_ONLY"},
    )
    assert i["potential_events"][0]["event_probability"] is None
    assert i["hypotheses"][0]["status"] == "INCONCLUSIVE"
    assert interpret_forecast(c, result, None)["event_evaluation"] == "NOT_EVALUATED"
    broken = deepcopy(result)
    broken["quantiles"]["0.9"][0] = 49
    with pytest.raises(SemanticRuleViolation):
        validate_forecast_result(broken, 3)


def test_legacy_declaration_payload_unchanged_and_no_core_equipment_branch():
    d = SemanticDeclarations().model_dump(mode="json")
    assert "signalDefinitions" not in d and "forecastProfiles" not in d
    result = compose_declarations(
        packs={"local": {**d, "types": [{"key": "demo.io/asset", "abstract": False}]}},
        dependencies={"local": ()},
    )
    assert "temporalContractVersion" not in result.normalized_snapshot


def test_profile_rejects_ambiguous_roles():
    with pytest.raises(ValueError):
        ForecastProfile(
            key="demo.io/profile",
            displayName="Test",
            target="demo.io/temp",
            futureCovariates=("demo.io/temp",),
        )
