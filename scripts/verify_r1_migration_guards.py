"""Verify the nonempty 0014 rollback guard on a disposable clone, never the source DB."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg

ROOT = Path(__file__).resolve().parents[1]


async def main(output: Path) -> None:
    url = urlsplit(os.environ["NEXWEAVE_REVIEW_DATABASE_URL"])
    source = url.path.removeprefix("/")
    if url.hostname not in {"127.0.0.1", "localhost"} or not re.fullmatch(
        r"nexweave_review[a-z0-9_]*", source
    ):
        raise ValueError("Use an isolated loopback nexweave_review* database only")
    clone = "nxw_r1_guard_" + uuid4().hex
    admin = await asyncpg.connect(urlunsplit(url._replace(scheme="postgresql")))
    created = False
    try:
        # Both identifiers are validated/generated locally; no request SQL fragments.
        await admin.execute(f'CREATE DATABASE "{clone}" TEMPLATE "{source}"')  # noqa: S608
        created = True
        clone_url = urlunsplit(url._replace(path="/" + clone))

        async def facts() -> dict:
            c = await asyncpg.connect(
                urlunsplit(url._replace(scheme="postgresql", path="/" + clone))
            )
            try:
                return {
                    "revision": await c.fetchval("SELECT version_num FROM alembic_version"),
                    "audit_rows": await c.fetchval("SELECT count(*) FROM model_gateway_calls"),
                    "new_projection_rows": await c.fetchval(
                        "SELECT count(*) FROM release_search_documents WHERE embedding IS NULL"
                    ),
                }
            finally:
                await c.close()

        before = await facts()
        assert before["revision"] == "0015_r1_delivery" and before["audit_rows"] > 0
        result = await asyncio.to_thread(
            subprocess.run,  # noqa: S603 - fixed interpreter/module/revision, isolated clone URL
            [sys.executable, "-m", "alembic", "downgrade", "0013_r1_wiki"],
            env={
                **os.environ,
                "NEXWEAVE_DATABASE_URL": clone_url,
                "PYTHONPATH": os.pathsep.join(
                    str(ROOT / p)
                    for p in (
                        "apps/api/src",
                        "packages/domain/src",
                        "packages/contracts/src",
                        "packages/application/src",
                    )
                ),
            },
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "New model audit/projection data exists" in result.stderr, result.stderr[-2000:]
        after = await facts()
        assert after == before, (before, after)
        evidence = {
            "scope": "DISPOSABLE_CLONE_OF_SYNTHETIC_REVIEW_DATABASE",
            "source_database_modified": False,
            "rollback": "REFUSED_WITH_HISTORY_RETAINED",
            "before": before,
            "after": after,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence))
    finally:
        if created:
            await admin.execute(f'DROP DATABASE "{clone}"')  # noqa: S608
        await admin.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args().output))
