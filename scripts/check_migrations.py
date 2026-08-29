"""Exercise M3 upgrade/rollback only in a generated disposable database."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
M3_TABLES = {
    "document_segments",
    "parse_failure_units",
    "parse_jobs",
    "source_anchors",
    "source_documents",
    "source_import_batch_items",
    "source_import_batches",
    "source_invalidations",
    "source_upload_sessions",
    "source_versions",
}
M3_TRIGGERS = {
    "document_segments_append_only",
    "parse_failure_units_append_only",
    "source_anchors_protect",
    "source_invalidations_append_only",
    "source_versions_classification_guard",
    "source_versions_protect_raw",
}


def run(database_url: str, *arguments: str) -> None:
    environment = {**os.environ, "NEXWEAVE_DATABASE_URL": database_url}
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *arguments],
        check=True,
        cwd=ROOT,
        env=environment,
    )


async def verify_m3_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name IN "
                            "('document_segments','parse_failure_units','parse_jobs',"
                            "'source_anchors','source_documents','source_import_batch_items',"
                            "'source_import_batches','source_invalidations',"
                            "'source_upload_sessions','source_versions')"
                        )
                    )
                ).scalars()
            )
            triggers = set(
                (
                    await connection.execute(
                        text(
                            "SELECT trigger_name FROM information_schema.triggers "
                            "WHERE trigger_schema='public' AND trigger_name IN "
                            "('document_segments_append_only','parse_failure_units_append_only',"
                            "'source_anchors_protect','source_invalidations_append_only',"
                            "'source_versions_classification_guard',"
                            "'source_versions_protect_raw')"
                        )
                    )
                ).scalars()
            )
            replacement_index = await connection.scalar(
                text(
                    "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' "
                    "AND indexname='uq_source_versions_one_replacement'"
                )
            )
        if expected_present:
            if tables != M3_TABLES or triggers != M3_TRIGGERS or replacement_index != 1:
                raise RuntimeError(
                    "M3 schema verification failed: "
                    f"tables={sorted(tables)}, triggers={sorted(triggers)}, "
                    f"replacement_index={replacement_index}"
                )
        elif tables or triggers or replacement_index:
            raise RuntimeError(
                "M3 downgrade left schema residue: "
                f"tables={sorted(tables)}, triggers={sorted(triggers)}, "
                f"replacement_index={replacement_index}"
            )
    finally:
        await engine.dispose()


async def main() -> None:
    source_url = os.environ.get("NEXWEAVE_DATABASE_URL")
    if not source_url:
        raise RuntimeError("NEXWEAVE_DATABASE_URL is required")
    source = make_url(source_url)
    disposable_name = f"nexweave_migration_verify_{uuid4().hex[:12]}"
    disposable_url = source.set(database=disposable_name).render_as_string(hide_password=False)
    admin_url = source.set(database="postgres").render_as_string(hide_password=False)
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{disposable_name}"'))
        run(disposable_url, "upgrade", "head")
        await verify_m3_schema(disposable_url, expected_present=True)
        run(disposable_url, "downgrade", "0003_m2")
        await verify_m3_schema(disposable_url, expected_present=False)
        run(disposable_url, "upgrade", "head")
        await verify_m3_schema(disposable_url, expected_present=True)
        print(
            "Disposable migration upgrade/downgrade/re-upgrade passed through M3 head "
            "with 10 tables, 6 guards, and the replacement uniqueness constraint"
        )
    finally:
        async with admin.connect() as connection:
            await connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:database AND pid <> pg_backend_pid()"
                ),
                {"database": disposable_name},
            )
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{disposable_name}"'))
        await admin.dispose()


if __name__ == "__main__":
    asyncio.run(main())
