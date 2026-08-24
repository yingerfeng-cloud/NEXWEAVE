# Changelog

All notable changes to NEXWEAVE will be documented in this file.

## [Unreleased]

### Added

- M-1 product, architecture, domain, data, API, event, Workflow, security, quality and traceability baselines.
- Governed copies of NEXWEAVE product/task materials and selected GridCrew reference materials.
- Accepted M0 ADR decisions and frozen domain/API/event/Workflow/version contracts.
- Executable Python/TypeScript Monorepo with API, Web status shell, Temporal health Worker, base migration, Compose and CI quality gates.
- Exact dependency locks, secret bootstrap/scan, dependency audit, architecture/contract/unit/UI verification and M0 operator runbook.
- ADR-0017 and the RustFS 1.0.0-rc.3 S3-compatible M0 runtime, replacing the prior object-storage provider without a runtime fallback.

### Accepted

- M-1 governance baseline formally accepted by the user on 2026-08-23.
- Formal M0 execution dispatched by the user on 2026-08-23 and formally accepted by the user on 2026-08-24 with the documented P1 follow-ups retained.
- RustFS replacement explicitly approved by the user on 2026-08-24; production promotion remains gated by SPK-004 compatibility, recovery and supply-chain evidence.

### Fixed

- Updated Temporal 1.29.6 to use its shipped dynamic configuration path.
- Installed the Web runtime configuration as a complete non-root Nginx main configuration and made its health probe use the actual IPv4 loopback listener.
- Replaced an unsupported Alembic CLI flag with an explicit unique-head/database-revision comparison compatible with the locked Alembic 1.16.4.

### Not implemented

- No Source, Schema, Compile, Wiki, Review, Release, Query, GridCrew or RCA business functionality is implemented in M0.
