# Migration and Fixture Strategy

## Migration rules

- Alembic revisions are append-only after acceptance; never edit historical migrations to make a new environment pass.
- Each revision has deterministic upgrade and downgrade logic appropriate to its risk. A deliberately irreversible production step must fail loudly and have an approved restore/forward plan.
- Schema changes, backfills and destructive cleanup are separate revisions. Large backfills are resumable/idempotent application jobs, not an unbounded migration transaction.
- Upgrade supports the declared previous release window; rollback compatibility, traffic order and data preservation are documented per change.
- M0 `0001_m0_platform_foundation` creates only tenant, organization, identity, knowledge-space, audit, outbox, configuration and platform-version structures.
- M0 testing exercises `base → head → base → head` against a disposable real PostgreSQL instance. The rollback target is forbidden against shared/production data.

## Tenant and safety rules

- App-generated UUIDv7 IDs have no database sequence fallback.
- Cross-scope foreign keys include tenant context where a child can reference a space/organization.
- Inline secrets are forbidden from configuration rows; only Secret Provider references are allowed in later stages.
- Audit/outbox are append-oriented facts. Retention, sealing, legal hold and partitioning are later governance migrations, never client-side deletion.

## Fixture rules

- `infra/fixtures/m0_platform_seed.json` is the versioned M0 seed manifest. Every value is synthetic, explicitly classified and safe to commit; it defines stable UUIDv7 references for later adapter-level integration setup without pretending that M1 identity/space APIs exist.
- Unit tests use builders/factories with deterministic synthetic values; no customer text, internal endpoint or copied production row.
- Contract fixtures live beside versioned schemas and carry explicit schema version/checksum.
- Integration fixtures are inserted through repository/application boundaries when those exist. SQL fixtures are limited to migration mechanics.
- E2E environments create isolated tenant/space IDs and delete the disposable environment, not individual facts that might hide cleanup defects.
- Golden parser/evaluation corpora are versioned, licensed and classified before use; the missing RCA pilot corpus remains an open M9 input.

M0 does not automatically insert the manifest into PostgreSQL. Automatic seed loading must go through the M1 application/repository boundary with audit semantics; bypassing that boundary in M0 would freeze an implementation that is outside this Milestone. Migration tests therefore validate schema mechanics independently of future business seed loading.

## Verification commands

- `alembic upgrade head`: normal forward migration.
- `make migration-check`: destructive rollback/re-upgrade check in local Compose only.
- `make verify`: confirms migration head plus the Web/API/infrastructure/Temporal Worker chain.
