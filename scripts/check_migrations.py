"""Exercise M0→M7 upgrade, M7 downgrade, re-upgrade and legacy-data preservation."""

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
M4_TABLES = {
    "schema_definitions",
    "schema_versions",
    "entity_types",
    "property_definitions",
    "type_hierarchy_edges",
    "relation_types",
    "type_terms",
    "concept_mappings",
    "page_templates",
    "lint_rules",
    "evaluation_suites",
    "ui_declarations",
    "schema_migration_plans",
    "schema_composition_reports",
    "domain_packs",
    "domain_pack_trust_keys",
    "domain_pack_versions",
    "domain_pack_contents",
    "domain_pack_dependencies",
    "domain_pack_revocations",
    "schema_version_pack_inputs",
    "domain_pack_installations",
}
M5_TABLES = {
    "compile_jobs",
    "compile_job_sources",
    "compile_steps",
    "model_invocations",
    "knowledge_entities",
    "knowledge_entity_versions",
    "candidate_relations",
    "claim_candidates",
    "evidence_candidates",
    "semantic_change_proposals",
    "wiki_pages",
    "wiki_page_versions",
    "wiki_page_links",
    "wiki_page_comments",
    "wiki_page_follows",
    "conflict_candidates",
    "lint_findings",
}
M5_TRIGGERS = {
    "compile_job_sources_immutable",
    "model_invocations_immutable",
    "knowledge_entity_versions_immutable",
    "wiki_page_versions_immutable",
    "evidence_candidates_immutable",
}
M6_TABLES = {
    "review_policies",
    "claims",
    "evidence_records",
    "conflict_cases",
    "conflict_items",
    "conflict_decisions",
    "review_cases",
    "review_tasks",
    "review_actions",
}
M6_TRIGGERS = {
    "claims_m6_immutable",
    "evidence_records_m6_immutable",
    "conflict_items_m6_immutable",
    "conflict_decisions_m6_immutable",
    "review_actions_m6_immutable",
}
M7_TABLES = {
    "relations",
    "evaluation_cases",
    "evaluation_runs",
    "evaluation_results",
    "release_candidates",
    "release_candidate_items",
    "release_lint_findings",
    "release_approvals",
    "releases",
    "release_items",
    "release_pointers",
    "release_pointer_history",
    "release_deprecations",
    "release_search_documents",
    "query_sessions",
    "query_answers",
    "citations",
}
M7_TRIGGERS = {
    "relations_m7_immutable",
    "evaluation_cases_m7_immutable",
    "evaluation_results_m7_immutable",
    "release_lint_findings_m7_immutable",
    "release_candidate_items_m7_immutable",
    "release_approvals_m7_immutable",
    "releases_m7_immutable",
    "release_items_m7_immutable",
    "release_pointer_history_m7_immutable",
    "release_deprecations_m7_immutable",
    "query_sessions_m7_immutable",
    "query_answers_m7_immutable",
    "citations_m7_immutable",
}
M8_TABLES = {
    "connector_instances",
    "connector_sync_runs",
    "obsidian_exports",
    "obsidian_imports",
    "obsidian_import_conflicts",
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


async def verify_m4_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name = ANY(:tables)"
                        ),
                        {"tables": sorted(M4_TABLES)},
                    )
                ).scalars()
            )
            head = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        if expected_present and tables != M4_TABLES:
            raise RuntimeError(
                f"M4 schema verification failed: tables={sorted(tables)}, head={head}"
            )
        if not expected_present and tables:
            raise RuntimeError(f"M4 downgrade left schema residue: {sorted(tables)}")
    finally:
        await engine.dispose()


async def verify_m5_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name = ANY(:tables)"
                        ),
                        {"tables": sorted(M5_TABLES)},
                    )
                ).scalars()
            )
            triggers = set(
                (
                    await connection.execute(
                        text(
                            "SELECT trigger_name FROM information_schema.triggers "
                            "WHERE trigger_schema='public' AND trigger_name = ANY(:triggers)"
                        ),
                        {"triggers": sorted(M5_TRIGGERS)},
                    )
                ).scalars()
            )
            head = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        if expected_present and (
            tables != M5_TABLES
            or triggers != M5_TRIGGERS
            or head not in {"0006_m5", "0007_m6", "0008_m7", "0009_m8", "0010_m95", "0011_m95a"}
        ):
            raise RuntimeError(
                f"M5 schema verification failed: tables={sorted(tables)}, "
                f"triggers={sorted(triggers)}, head={head}"
            )
        if not expected_present and (tables or triggers):
            raise RuntimeError(
                f"M5 downgrade left residue: tables={sorted(tables)}, triggers={sorted(triggers)}"
            )
    finally:
        await engine.dispose()


async def verify_m6_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name = ANY(:tables)"
                        ),
                        {"tables": sorted(M6_TABLES)},
                    )
                ).scalars()
            )
            triggers = set(
                (
                    await connection.execute(
                        text(
                            "SELECT trigger_name FROM information_schema.triggers "
                            "WHERE trigger_schema='public' AND trigger_name = ANY(:triggers)"
                        ),
                        {"triggers": sorted(M6_TRIGGERS)},
                    )
                ).scalars()
            )
            head = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        if expected_present and (
            tables != M6_TABLES
            or triggers != M6_TRIGGERS
            or head not in {"0007_m6", "0008_m7", "0009_m8", "0010_m95", "0011_m95a"}
        ):
            raise RuntimeError(
                f"M6 schema verification failed: tables={sorted(tables)}, "
                f"triggers={sorted(triggers)}, head={head}"
            )
        if not expected_present and (tables or triggers):
            raise RuntimeError(
                f"M6 downgrade left residue: tables={sorted(tables)}, triggers={sorted(triggers)}"
            )
    finally:
        await engine.dispose()


async def verify_m7_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name = ANY(:tables)"
                        ),
                        {"tables": sorted(M7_TABLES)},
                    )
                ).scalars()
            )
            triggers = set(
                (
                    await connection.execute(
                        text(
                            "SELECT trigger_name FROM information_schema.triggers "
                            "WHERE trigger_schema='public' AND trigger_name = ANY(:triggers)"
                        ),
                        {"triggers": sorted(M7_TRIGGERS)},
                    )
                ).scalars()
            )
            head = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            vector_columns = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name="
                    "'release_search_documents' AND column_name='embedding' AND udt_name='vector'"
                )
            )
        if expected_present and (
            tables != M7_TABLES
            or triggers != M7_TRIGGERS
            or head not in {"0008_m7", "0009_m8", "0010_m95", "0011_m95a"}
            or vector_columns != 1
        ):
            raise RuntimeError(
                f"M7 schema verification failed: tables={sorted(tables)}, "
                f"triggers={sorted(triggers)}, head={head}, vector_columns={vector_columns}"
            )
        if not expected_present and (tables or triggers or vector_columns):
            raise RuntimeError(
                f"M7 downgrade left residue: tables={sorted(tables)}, "
                f"triggers={sorted(triggers)}, vector_columns={vector_columns}"
            )
    finally:
        await engine.dispose()


async def verify_m8_schema(database_url: str, *, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name = ANY(:tables)"
                        ),
                        {"tables": sorted(M8_TABLES)},
                    )
                ).scalars()
            )
            head = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        if expected_present and (
            tables != M8_TABLES or head not in {"0009_m8", "0010_m95", "0011_m95a"}
        ):
            raise RuntimeError(
                f"M8 schema verification failed: tables={sorted(tables)}, head={head}"
            )
        if not expected_present and tables:
            raise RuntimeError(f"M8 downgrade left residue: tables={sorted(tables)}")
    finally:
        await engine.dispose()


async def verify_m95a_schema(database_url: str, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as c:
            count = await c.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name IN "
                    "('forecast_delivery','forecast_worker_leases')"
                )
            )
            if count != (2 if expected_present else 0):
                raise RuntimeError("Stage A migration table mismatch")
        if expected_present:
            from types import SimpleNamespace

            from nexweave_api.forecast_recovery import ForecastRecovery

            # Exercise the real parameterized SQL, including NULL, against the disposable schema.
            repo = SimpleNamespace(database=SimpleNamespace(engine=engine))
            recovery = ForecastRecovery(repo, None, None)
            await recovery.update(uuid4(), "RETRYING", "TEMPORAL_UNAVAILABLE")
            await recovery.update(uuid4(), "ACCEPTED")
    finally:
        await engine.dispose()


async def verify_m95_schema(database_url: str, expected_present: bool) -> None:
    engine = create_async_engine(database_url)
    names = ["signal_bindings", "forecast_runs", "forecast_artifacts"]
    try:
        async with engine.connect() as c:
            tables = set(
                (
                    await c.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema='public' AND table_name=ANY(:names)"
                        ),
                        {"names": names},
                    )
                ).scalars()
            )
        assert tables == (set(names) if expected_present else set())
    finally:
        await engine.dispose()


async def seed_legacy_data(database_url: str) -> tuple[str, str]:
    tenant_id, organization_id, space_id, source_id, actor_id = (str(uuid4()) for _ in range(5))
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO tenants (id,slug,display_name,created_by,updated_by) "
                    "VALUES (:id,:slug,'M4 migration sentinel',:actor,:actor)"
                ),
                {"id": tenant_id, "slug": f"m4-{tenant_id[:8]}", "actor": actor_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id,tenant_id,slug,display_name,created_by,updated_by) "
                    "VALUES (:id,:tenant,'sentinel','Sentinel',:actor,:actor)"
                ),
                {
                    "id": organization_id,
                    "tenant": tenant_id,
                    "actor": actor_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO knowledge_spaces "
                    "(id,tenant_id,organization_id,slug,display_name,default_classification,"
                    "created_by,updated_by) VALUES "
                    "(:id,:tenant,:organization,'sentinel','Sentinel','INTERNAL',:actor,:actor)"
                ),
                {
                    "id": space_id,
                    "tenant": tenant_id,
                    "organization": organization_id,
                    "actor": actor_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO source_documents "
                    "(id,tenant_id,space_id,display_name,classification,created_by,updated_by) "
                    "VALUES (:id,:tenant,:space,'M3 sentinel','INTERNAL',:actor,:actor)"
                ),
                {
                    "id": source_id,
                    "tenant": tenant_id,
                    "space": space_id,
                    "actor": actor_id,
                },
            )
    finally:
        await engine.dispose()
    return tenant_id, source_id


async def verify_legacy_data(database_url: str, tenant_id: str, source_id: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            count = await connection.scalar(
                text(
                    "SELECT COUNT(*) FROM source_documents "
                    "WHERE tenant_id=:tenant AND id=:source AND display_name='M3 sentinel'"
                ),
                {"tenant": tenant_id, "source": source_id},
            )
        if count != 1:
            raise RuntimeError("M0-M3 sentinel data changed during M4 migration cycle")
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
        await verify_m4_schema(disposable_url, expected_present=True)
        await verify_m5_schema(disposable_url, expected_present=True)
        await verify_m6_schema(disposable_url, expected_present=True)
        await verify_m7_schema(disposable_url, expected_present=True)
        await verify_m8_schema(disposable_url, expected_present=True)
        await verify_m95_schema(disposable_url, True)
        tenant_id, source_id = await seed_legacy_data(disposable_url)
        await verify_m95a_schema(disposable_url, True)
        run(disposable_url, "downgrade", "0010_m95")
        await verify_m95a_schema(disposable_url, False)
        await verify_m95_schema(disposable_url, True)
        run(disposable_url, "downgrade", "0009_m8")
        await verify_m95_schema(disposable_url, False)
        run(disposable_url, "downgrade", "0008_m7")
        await verify_m8_schema(disposable_url, expected_present=False)
        run(disposable_url, "downgrade", "0007_m6")
        await verify_m7_schema(disposable_url, expected_present=False)
        await verify_m6_schema(disposable_url, expected_present=True)
        await verify_m5_schema(disposable_url, expected_present=True)
        await verify_m4_schema(disposable_url, expected_present=True)
        await verify_m3_schema(disposable_url, expected_present=True)
        await verify_legacy_data(disposable_url, tenant_id, source_id)
        run(disposable_url, "upgrade", "head")
        await verify_m3_schema(disposable_url, expected_present=True)
        await verify_m4_schema(disposable_url, expected_present=True)
        await verify_m5_schema(disposable_url, expected_present=True)
        await verify_m6_schema(disposable_url, expected_present=True)
        await verify_m7_schema(disposable_url, expected_present=True)
        await verify_m8_schema(disposable_url, expected_present=True)
        await verify_legacy_data(disposable_url, tenant_id, source_id)
        await verify_m95_schema(disposable_url, True)
        print(
            "Disposable M0→M9.5 upgrade/downgrade/re-upgrade passed, "
            "pgvector projection and M0-M4 sentinel data preserved"
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
