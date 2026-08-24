import json
from pathlib import Path

from jsonschema.validators import validator_for

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "packages/contracts/schemas"


def test_all_public_json_schemas_are_valid() -> None:
    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert schema_paths
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator_for(schema).check_schema(schema)
