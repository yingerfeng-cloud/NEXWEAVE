# Changelog

All notable changes to NEXWEAVE will be documented in this file.

## [Unreleased]

### Added

- M2 dedicated Temporal namespace, separate Workflow/Activity task queues and non-root kernel Worker for seven versioned Workflow definitions.
- M2 reliable control kernel with stable Workflow IDs, Update/Signal commands, durable approval waits, timeout escalation, Activity retry/heartbeat, cancellation compensation and replay-safe deterministic code.
- `WorkflowTask`, `WorkflowStep` and append-only `WorkflowTaskEvent` PostgreSQL projections, reconciliation/repair, audit/Outbox, `0003_m2_temporal_kernel` migration and authenticated task APIs.
- Real API-driven task center, workflow OpenAPI/event schemas, Python/TypeScript SDK calls, reliability tests and M2 runbook/execution/fault-drill reports.
- M1 OIDC-compatible identity boundary, local development identity provider, default-deny RBAC+ABAC, service identities and tenant/space membership policy.
- M1 KnowledgeSpace create/edit/archive and member grant/revoke APIs plus authenticated responsive Web workflows and 16 deep-link routes.
- M1 governance configuration, append-only audit/Outbox/idempotency facts, OpenTelemetry correlation and sanitized diagnostics.
- Provider-neutral object/scanner ports, RustFS conditional-write adapter, controlled upload/checksum/scan/download chain and `ManagedObject` metadata (not SourceVersion).
- `0002_m1_platform_services` migration, versioned OpenAPI/event/JSON Schema contracts, typed Python/TypeScript SDK foundations, M1 runbook and real Compose E2E verification.
- M-1 product, architecture, domain, data, API, event, Workflow, security, quality and traceability baselines.
- Governed copies of NEXWEAVE product/task materials and selected GridCrew reference materials.
- Accepted M0 ADR decisions and frozen domain/API/event/Workflow/version contracts.
- Executable Python/TypeScript Monorepo with API, Web status shell, Temporal health Worker, base migration, Compose and CI quality gates.
- Exact dependency locks, secret bootstrap/scan, dependency audit, architecture/contract/unit/UI verification and M0 operator runbook.
- ADR-0017 and the RustFS 1.0.0-rc.3 S3-compatible M0 runtime, replacing the prior object-storage provider without a runtime fallback.
- ADR-0018, the reproducible RustFS SPK-004 harness/report, and GitHub container gates for dual-architecture CycloneDX SBOMs, fixable HIGH/CRITICAL CVEs and keyless Cosign signatures.

### Accepted

- M-1 governance baseline formally accepted by the user on 2026-08-23.
- Formal M0 execution dispatched by the user on 2026-08-23 and formally accepted by the user on 2026-08-24 with the documented P1 follow-ups retained.
- RustFS replacement explicitly approved by the user on 2026-08-24; production promotion remains gated by SPK-004 compatibility, recovery and supply-chain evidence.
- M0 P1 closure backed by GitHub Actions run 32702688049: all six quality, Compose, application-image and RustFS approval jobs passed.
- M1 formally accepted and M2 formally dispatched by the user on 2026-08-24.
- Local Git commit of the accepted M1 and completed M2 delivery authorized by the user on 2026-08-25; no push authorized.

### Fixed

- Made duplicate M2 commands return the original business result before stale ETag evaluation, preserving command idempotency across retries.
- Removed an internal command-record field before public response validation and made Workflow projection updates type-stable for asyncpg.
- Made Temporal closed execution status override stale Workflow query snapshots during reconciliation, so terminated/failed runs can enter the authorized retry path.
- Preserved enum types in in-memory contracts while retaining JSON string serialization; normalized UUID/Enum/timezone values in canonical idempotency hashes.
- Made the M1 migration downgrade tolerant of a pre-acceptance local revision that did not contain the final connector partial indexes.
- Updated Temporal 1.29.6 to use its shipped dynamic configuration path.
- Installed the Web runtime configuration as a complete non-root Nginx main configuration and made its health probe use the actual IPv4 loopback listener.
- Replaced an unsupported Alembic CLI flag with an explicit unique-head/database-revision comparison compatible with the locked Alembic 1.16.4.
- Upgraded Temporal SDK 1.17.0 to 1.31.0 and Nginx 1.29.1/Alpine 3.22 to 1.31.4/Alpine 3.24 after container scans found fixed HIGH/CRITICAL advisories; rescans are clean under the approved policy.
- Corrected the CI installer compatibility boundary by using cosign-installer v4.1.2 for Cosign v3.0.2.

### Not implemented

- M2 Workflow Activities are explicit kernel Stubs. No Source/parse, Schema, real Compile, Wiki, Claim/Evidence, Graph, Conflict, Review business objects, Quality evaluation, immutable Release, Query, Domain Pack installation, GridCrew intake, real Connector/model execution or RCA functionality is implemented.
