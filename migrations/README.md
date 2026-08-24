# M0 migration baseline

Migrations are append-only once accepted. `0001_m0_platform_foundation` contains only platform-level tenancy, identity, space, audit, transactional outbox, configuration and version structures. It intentionally contains no Source, Schema, Claim, Evidence, Release or Query business tables.

Use `alembic upgrade head` for upgrade. `make migration-check` exercises downgrade-to-base and re-upgrade only against the local disposable M0 Compose database; never run that target against shared or production data.
