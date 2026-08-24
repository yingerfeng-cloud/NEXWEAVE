import json
from pathlib import Path
from uuid import UUID


def test_m0_seed_is_explicitly_synthetic_and_uses_uuid7() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2] / "infra" / "fixtures" / "m0_platform_seed.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert fixture["fixture_version"] == "1.0.0"
    assert fixture["classification"] == "PUBLIC"
    assert fixture["synthetic"] is True
    for resource_name in ("tenant", "organization", "identity", "space"):
        assert UUID(fixture[resource_name]["id"]).version == 7
