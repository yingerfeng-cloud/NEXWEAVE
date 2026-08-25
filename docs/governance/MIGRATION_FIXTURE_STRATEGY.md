# Migration and Fixture Strategy

## Migration rules

- Alembic revisions are append-only after acceptance; never edit historical migrations to make a new environment pass.
- Each revision has deterministic upgrade and downgrade logic appropriate to its risk. A deliberately irreversible production step must fail loudly and have an approved restore/forward plan.
- Schema changes, backfills and destructive cleanup are separate revisions. Large backfills are resumable/idempotent application jobs, not an unbounded migration transaction.
- Upgrade supports the declared previous release window; rollback compatibility, traffic order and data preservation are documented per change.
- M0 `0001_m0_platform_foundation` creates only tenant, organization, identity, knowledge-space, audit, outbox, configuration and platform-version structures.
- M1 `0002_m1_platform_services` adds service audiences, tenant/space roles, idempotency, governance configuration, upload sessions and managed-object metadata without modifying `0001`.
- M2 `0003_m2_temporal_kernel` adds WorkflowTask/Step/append-only Event projections and their tenant/space/run/idempotency indexes without modifying `0001` or `0002`.
- M2 testing exercises `base → head → base → head` against a dedicated disposable real PostgreSQL database. The rollback target is forbidden against the active development, shared or production database.
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

M1 local startup provisions a synthetic development tenant only through the repository bootstrap boundary; M2 E2E creates synthetic tasks and reference strings in that local scope. Migration tests validate schema mechanics in a disposable database independently and never ingest customer or production rows.

## Verification commands

- `alembic upgrade head`: normal forward migration.
- `make migration-check`: destructive rollback/re-upgrade check in local Compose only.
- `make verify`: confirms the M1 foundation and then the M2 real Temporal task chain.
- `make verify-m2`: confirms all seven Workflow types, controls, retries, compensation, projection repair, Worker restart and replay against the running Compose stack.
