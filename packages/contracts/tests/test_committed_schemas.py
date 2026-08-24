from pathlib import Path

from nexweave_contracts.schema_export import render_schemas

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def test_committed_schemas_match_canonical_models() -> None:
    expected = render_schemas()
    actual = {path.name: path.read_text(encoding="utf-8") for path in SCHEMA_DIR.glob("*.json")}
    assert actual == expected
