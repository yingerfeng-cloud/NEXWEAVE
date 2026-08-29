# Migration and Fixture Strategy

## Migration rules

- Alembic revisions are append-only after acceptance; never edit historical migrations to make a new environment pass.
- Each revision has deterministic upgrade and downgrade logic appropriate to its risk. A deliberately irreversible production step must fail loudly and have an approved restore/forward plan.
- Schema changes, backfills and destructive cleanup are separate revisions. Large backfills are resumable/idempotent application jobs, not an unbounded migration transaction.
- Upgrade supports the declared previous release window; rollback compatibility, traffic order and data preservation are documented per change.
- M0 `0001_m0_platform_foundation` creates only tenant, organization, identity, knowledge-space, audit, outbox, configuration and platform-version structures.
- M1 `0002_m1_platform_services` adds service audiences, tenant/space roles, idempotency, governance configuration, upload sessions and managed-object metadata without modifying `0001`.
- M2 `0003_m2_temporal_kernel` adds WorkflowTask/Step/append-only Event projections and their tenant/space/run/idempotency indexes without modifying `0001` or `0002`.
- M3 adds the additive `0004_m3_source_parsing` revision for Source/Parse tables, immutable-fact triggers, classification/replacement constraints and indexes without modifying `0001`—`0003`; M1 ManagedObject rows are neither promoted nor deleted.
- `make migration-check` generates a uniquely named disposable PostgreSQL database, executes `upgrade head → downgrade 0003_m2 → upgrade head`, and drops only that generated database. The rollback target is forbidden against the active development, shared or production database.
- The `0002` downgrade uses `DROP INDEX IF EXISTS` for its two connector partial indexes so a local pre-acceptance database that briefly carried the same development revision identifier can be recovered. This is compatibility hardening, not permission to rewrite an accepted historical migration.

## Tenant and safety rules

- App-generated UUIDv7 IDs have no database sequence fallback.
- Cross-scope foreign keys include tenant context where a child can reference a space/organization.
- Inline secrets are forbidden from configuration rows; M1 `ModelProfile` and `ServiceIdentity` persist only Secret Provider references.
- Audit/outbox are append-oriented facts. Retention, sealing, legal hold and partitioning are later governance migrations, never client-side deletion.
- `workflow_task_events` is append-only by database trigger; reconcile repairs mutable task/step projections by adding a reconciliation event, never rewriting history.

## Fixture rules

- `infra/fixtures/m0_platform_seed.json` is the versioned M0 seed manifest. Every value is synthetic, explicitly classified and safe to commit; it defines stable UUIDv7 references for later adapter-level integration setup without pretending that M1 identity/space APIs exist.
- Unit tests use builders/factories with deterministic synthetic values; no customer text, internal endpoint or copied production row.
- Contract fixtures live beside versioned schemas and carry explicit schema version/checksum.
- Integration fixtures are inserted through repository/application boundaries when those exist. SQL fixtures are limited to migration mechanics.
- E2E environments create isolated tenant/space IDs and delete the disposable environment, not individual facts that might hide cleanup defects.
- Golden parser/evaluation corpora are versioned, licensed and classified before use; the missing RCA pilot corpus remains an open M9 input.
- M3 parser fixtures must include synthetic/licensed PDF, DOCX, Markdown, TXT, CSV and XLSX files plus malformed/security cases and a scanned PDF. A scanned PDF without a real OCR Provider expects truthful `OCR_REQUIRED/PARTIAL`, not fixed OCR text.

M1 local startup provisions a synthetic development tenant only through the repository bootstrap boundary; M2 E2E creates synthetic tasks and reference strings in that local scope. Migration tests validate schema mechanics in a disposable database independently and never ingest customer or production rows.

## Verification commands

- `alembic upgrade head`: normal forward migration.
- `make migration-check`: isolated M3 rollback/re-upgrade check in a generated disposable database.
- `make verify`: confirms the M1 foundation, M2 Temporal task chain and M3 Source/parse chain.
- `make verify-m2`: confirms all seven Workflow types, controls, retries, compensation, projection repair, Worker restart and replay against the running Compose stack.
- `make verify-m3`: confirms real Raw registration, ClamAV, v2 Workflow, six parser types, scanned-PDF `OCR_REQUIRED`, reparse, invalidation, batch and Outbox behavior; it does not claim real OCR or archived accepted-M2 history replay.
