import json
from pathlib import Path

from nexweave_api.openapi_export import render_openapi

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "packages/contracts/openapi/nexweave-platform-v1.openapi.json"


def test_implementation_matches_reviewed_openapi_snapshot() -> None:
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == render_openapi()
    assert committed["openapi"].startswith("3.1.")
    assert set(committed["paths"]) == {
        "/api/v1/config/diagnostics",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/version",
    }
