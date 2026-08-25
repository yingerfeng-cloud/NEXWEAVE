import json
from pathlib import Path

from nexweave_api.openapi_export import render_openapi

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "packages/contracts/openapi/nexweave-platform-v1.openapi.json"


def test_implementation_matches_reviewed_openapi_snapshot() -> None:
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == render_openapi()
    assert committed["openapi"].startswith("3.1.")
    assert {
        "/api/v1/auth/dev/session",
        "/api/v1/auth/me",
        "/api/v1/spaces",
        "/api/v1/spaces/{space_id}",
        "/api/v1/spaces/{space_id}/members/{subject_id}",
        "/api/v1/objects/{object_id}/content",
        "/api/v1/audit-logs",
        "/api/v1/spaces/{space_id}/workflow-tasks",
        "/api/v1/workflow-tasks/{task_id}",
        "/api/v1/workflow-tasks/{task_id}/commands",
        "/api/v1/workflow-tasks/{task_id}/reconcile",
    }.issubset(committed["paths"])
    assert "/api/v1/sources" not in committed["paths"]
    assert committed["components"]["securitySchemes"]["OIDC Bearer"] == {
        "scheme": "bearer",
        "type": "http",
    }
    assert committed["paths"]["/api/v1/spaces"]["get"]["security"] == [{"OIDC Bearer": []}]
    assert "409" in committed["paths"]["/api/v1/spaces"]["post"]["responses"]
