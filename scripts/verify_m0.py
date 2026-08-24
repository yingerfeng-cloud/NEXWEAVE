"""Verify the real local M0 vertical health chain without business mocks."""

from __future__ import annotations

import json
import subprocess
import urllib.request


def get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def run(*arguments: str) -> None:
    subprocess.run(arguments, check=True)  # noqa: S603


def alembic_revisions(command: str) -> set[str]:
    result = subprocess.run(  # noqa: S603
        ("docker", "compose", "exec", "-T", "api", "alembic", command),
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.split(maxsplit=1)[0] for line in result.stdout.splitlines() if line.strip()}


def verify_database_at_migration_head() -> None:
    heads = alembic_revisions("heads")
    current = alembic_revisions("current")
    if len(heads) != 1:
        raise RuntimeError(f"Expected one Alembic head, found: {sorted(heads)!r}")
    if current != heads:
        raise RuntimeError(
            f"Database revisions {sorted(current)!r} do not match Alembic head {sorted(heads)!r}"
        )


def main() -> None:
    readiness = get_json("http://localhost:8000/api/v1/health/ready")
    if readiness.get("status") != "ready":
        raise RuntimeError(f"API readiness failed: {readiness!r}")
    components = readiness.get("components")
    if not isinstance(components, dict) or set(components) != {
        "postgresql",
        "redis",
        "object_storage",
        "temporal",
    }:
        raise RuntimeError(f"Unexpected readiness components: {components!r}")

    with urllib.request.urlopen("http://localhost:8080/", timeout=10) as response:  # noqa: S310
        page = response.read().decode("utf-8")
    if "NEXWEAVE" not in page:
        raise RuntimeError("Web shell did not return the NEXWEAVE application")

    verify_database_at_migration_head()
    run(
        "docker",
        "compose",
        "exec",
        "-T",
        "worker-health",
        "python",
        "-m",
        "nexweave_worker_health.verify",
    )
    print("M0 E2E passed: Web -> API -> PostgreSQL/Redis/RustFS(S3)/Temporal -> Worker")


if __name__ == "__main__":
    main()
