from pathlib import Path


def test_health_workflow_contains_no_forbidden_io_imports() -> None:
    workflow_source = (
        Path(__file__).resolve().parents[1] / "src/nexweave_worker_health/workflows.py"
    ).read_text(encoding="utf-8")
    forbidden = ("httpx", "sqlalchemy", "redis", "open(", "requests", "boto")
    assert not any(item in workflow_source for item in forbidden)
