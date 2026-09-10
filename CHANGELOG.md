# Changelog

All notable changes to NEXWEAVE will be documented in this file.

## [Unreleased]

### Added

- Completed Stage D fixed-Release Query/Graph current-visibility gates, historical answer read projections, input-safe replay, bounded frozen graph traversal and source navigation repair (0.9.5-d1); key browser paths and synthetic HTTP/PostgreSQL checks passed. No migration or dependency changes.

- Added M9.5 Stage C fixed-Release knowledge context with currently valid, clearance-filtered citations, immutable Claim/Evidence snapshots, source preview links and existing-page interaction (0.9.5-c1). Verified using synthetic Review/Release records and existing Chronos artifacts; no new model inference, migration or dependency.
- Added M9.5 Stage B governed CSV preview, binding validation and an existing-page binding wizard with compatible same-history scenario comparison; verified with synthetic data and actual local Chronos-2 runs (0.9.5-b1).
- Closed forecast source invalidation/archive guards and Source public-response projection defects without changing Evidence/Release, migrations, dependencies or the model revision. Stage B report records validation and remaining industrial/production limits.
- Added `FRONTEND_UI_AUDIT.md`, `FRONTEND_DESIGN_SYSTEM.md` and `FRONTEND_REFACTOR_REPORT.md` for the 2026-09-07 desktop-first UX/UI system refactor, including a PASS/PARTIAL/FAIL acceptance matrix and four specified desktop viewport screenshots.
- Added a production-safe frontend error taxonomy, localhost-only Developer Mode, default test-fixture isolation, governance stepper, guided compile workflow, Wiki three-pane workbench and Ask evidence inspector without changing backend contracts.
- Added the audited M9 public RCA technical pilot for four admitted NTSB reports: immutable Raw failures under encrypted-PDF policy, text-only derivative SourceVersions, real signed Pack installation, 368 ClaimCandidates and 377 EvidenceCandidates with no formal Claim, ReviewCase or Release.
- Added a reproducible M9 public-pilot verifier and durable run evidence covering checksums, excluded pages, Source/Parse/Compile IDs, no-network model facts and audit completeness.
- Added the versioned M9-FE frontend design-system baseline, route/prototype/API/state mapping, component contracts, intentional-deviation record and three-viewport screenshot evidence for login and all 17 protected routes.
- Added shared AppShell, Sidebar/Topbar, PageHeader, Panel, Metric, Table and truthful loading/empty/error/permission state primitives without introducing a component library or remote runtime asset.
- Reworked the Web visual system to the high-fidelity prototype's deep-black, violet, cyan and lime language; split global styling into token, foundation, shell, component and feature layers; exposed the real Task Center at `/tasks` while retaining legacy task deep-link compatibility.
- Added ADR-0030, a rights-scoped catalog and an accession manifest for 9 official NTSB reports/610 pages; raw PDFs remain in Git-ignored local staging with verified page counts and SHA-256 values.
- Deferred GridCrew development and the joint pilot outside M9/R1 acceptance by explicit user decision; GridCrew is no longer a M9 P0 and is not reported as implemented or accepted.
- Restricted the public corpus to locally processed NTSB-authored text/tables until per-document admission; third-party imagery/attachments and external-model use remain denied by default.
- Added ADR-0029 and a signed, JSON-only `equipment-rca-pack@1.0.0` with 12 RCA domain types, evidence-required relations, governed terminology, page/assistant templates, six lint rules, safe UI metadata and a seven-case standard question set.
- Added deterministic core/equipment-RCA/maintenance composition verification, platform-decoupling/uninstall tests, an explicitly non-pilot synthetic fixture, M9 runbook and an empty evidence-preserving pilot acceptance template.
- Recorded expert thresholds and real review evidence as the remaining M9 P0; no synthetic fixture, unadmitted public source, Mock endpoint or self-selected metric is reported as a real pilot result.

- Added ADR-0026 and additive `0008_m7` for versioned Evaluation facts, explicit Release candidates/items, independent approvals, immutable Releases/items, pointer history/deprecation, formal Relations, pgvector/FTS projections and QuerySession/Answer/Citation facts.
- Added `nexweave.quality-evaluation.v2` and `nexweave.knowledge-release.v2`, authenticated M7 API/OpenAPI/JSON Schema/SDK contracts, and API-driven Quality, Release, Graph and Ask centers.
- Added fixed-Release hybrid retrieval with explainable RRF, classification/Evidence/VALID-Anchor filtering, citation-backed answers, insufficient-evidence refusal, JSON/Markdown export, projection rebuild and pointer-only rollback.
- Added isolated real M7 E2E verification and runbook/report covering two immutable Releases, independent approval, reproducible citations, refusal and rollback without modifying shared accepted data.

- Added M6 ADR-0025, additive `0007_m6` Claim/Evidence, ConflictCase/decision and staged ReviewPolicy/Case/Task/Action facts; source anchors, evidence snapshots, audit and immutable history remain preserved.
- Added Evidence-gated high-risk duty separation, configurable space review policies, `nexweave.human-review.v2`, M6 API/SDK contracts and API-driven Claim, Conflict and Review centers.

- Added M5 governed CompileJob/Step/ModelInvocation, stable candidate Entity/Relation/Claim/Evidence/Conflict/Lint and append-only Wiki Page/Version/link/comment/follow facts through additive `0006_m5`.
- Added provider-neutral Model Gateway ports with an explicitly no-network replayable local structured provider, `nexweave.knowledge-compile.v2`, fixed Source/Schema/Prompt/Model inputs and transactional `io.nexweave.compile.completed.v1` evidence.
- Added authenticated M5 APIs, OpenAPI/JSON Schema/events, Python/TypeScript SDKs, API-driven Compile Center and Wiki Workbench with protected sections, history/diff, evidence metadata and auditable new-job retry.
- Added ADR-0024, M5 runbook/verification/report, real Source→Compile→Wiki E2E and M0→M5 migration upgrade/downgrade/re-upgrade verification.
- Implemented M4 SchemaDefinition/immutable SchemaVersion, semantic facts, deterministic composition and preview-only compatibility/migration reporting as the single R1 semantic authority.
- Added JSON-only JCS-canonical Ed25519 Domain Packs, audited trust roots and signed offline revocation lists, exact dependency/checksum inputs and three safe test-only fixture Packs.
- Added `nexweave.domain-pack-install.v2` install/upgrade/disable/rollback Activities and projections while retaining M2 v1 workflow replay compatibility.
- Added authenticated M4 APIs, OpenAPI/JSON Schemas/events, Python and TypeScript SDKs, API-driven Schema Studio and Pack Center, additive `0005_m4`, real migration/E2E and M0—M3 regression verification.
- ADR-0022, the Semantic Model baseline and the M5—M15 impact matrix, freezing immutable SchemaVersion as the single R1 semantic authority and deterministic declarative Domain Pack composition without dispatching M4 implementation.
- A governance-calibrated M4 taskbook covering stable semantic keys, type/property/hierarchy/relation definitions, terminology/mappings, composition checksums, compatibility/migration, Pack security and real acceptance gates.
- An M4 Semantic Model governance calibration report recording the frozen decisions, M5—M15 update triggers, document-only validation and the no-implementation stop boundary.
- Calibrated and implemented the M3 Source/parse scope: immutable Raw/Source versions, upload sessions/batches, ParseJobs, Segment/Anchor/Invalidation facts, authenticated API/UI and typed SDKs.
- Added `nexweave.source-ingestion.v2`, real PDF/DOCX/Markdown/TXT/CSV/XLSX adapters, scanned-PDF detection with truthful `OCR_REQUIRED`, real ClamAV fail-closed scanning and additive `0004_m3_source_parsing`.
- Added a separate credential-free, non-root, read-only, resource-bounded parser sandbox on a dedicated internal IPC network; the trusted Activity coordinator retains DB/object/Temporal/ClamAV I/O.
- Added a reproducible ClamAV 1.4.3 image path from the accepted Debian 12 base and exact Debian security packages, with FreshClam-before-clamd startup, persistent signatures, read-only runtime hardening and a CI multi-architecture build-matrix entry.
- Added upload abort and ParseJob cancel APIs, immutable object-version reads, typed parser budgets, canonical result-manifest verification, global UTF-8 locators and replacement/classification concurrency guards.
- ADR-0021 freezing M3 failure/partial/retry/reparse, version replacement, v1/v2 Workflow compatibility, scanned-PDF `OCR_REQUIRED` and SourceAnchor relocation semantics.
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

- M7 was formally dispatched, implemented, locally technically accepted and formally accepted by the user on 2026-08-31; M8 was not dispatched.
- M6 was formally accepted by the user on 2026-08-31 before the separate M7 dispatch.
- M5 was formally dispatched, implemented, locally technically accepted and formally accepted by the user on 2026-08-30; remote CI and the disclosed external-provider/crash-window risks remain tracked without blocking that acceptance.
- M4 was formally dispatched on 2026-08-29 and formally accepted by the user on 2026-08-30 after M4-0, implementation, independent review/remediation and local technical acceptance; M5 was subsequently dispatched separately.
- M4 Semantic Model governance calibration was accepted and followed by formal M4 dispatch on 2026-08-29.
- M3 formally dispatched by the user on 2026-08-25 with explicit calibration, implementation and independent-review phases; it was completed and formally accepted on 2026-08-29 before M4 dispatch.
- M-1 governance baseline formally accepted by the user on 2026-08-23.
- Formal M0 execution dispatched by the user on 2026-08-23 and formally accepted by the user on 2026-08-24 with the documented P1 follow-ups retained.
- RustFS replacement explicitly approved by the user on 2026-08-24; production promotion remains gated by SPK-004 compatibility, recovery and supply-chain evidence.
- M0 P1 closure backed by GitHub Actions run 32702688049: all six quality, Compose, application-image and RustFS approval jobs passed.
- M1 formally accepted and M2 formally dispatched by the user on 2026-08-24.
- Git commit and push of the accepted M1 and completed M2 delivery authorized by the user on 2026-08-25; GitHub Actions run 32808198635 passed all eight quality, time-skipping, Compose and image-supply-chain jobs.
- M2 formally accepted by the user on 2026-08-25; M3 was subsequently completed and formally accepted before M4 dispatch.

### Fixed

- Rebuilt and replaced the Compose web image after the 2026-09-07 refactor; restored its required `api` dependency after a web-only start exposed nginx upstream DNS failure, and verified the updated 8080 UI through a real local login.
- Removed numbered/Milestone navigation and visible development vocabulary, moved Ask into Smart Use, mapped common status values to Chinese, standardized actionable empty states and reset scroll on primary-route navigation.
- Tightened the M9-FE Web experience after live 8080 review: mobile navigation now uses an explicit page selector, mobile quick navigation opens from a real button, form/error/title buttons share usable touch sizing, long Metric values no longer truncate, mobile tabs wrap visibly, Wiki graph nodes have a larger transparent hit area, and the browser title no longer says M0.
- Fixed the Web proxy's inherited 1 MB request ceiling by aligning it with the API's bounded 100 MB upload limit while retaining size, checksum, content-type, malware and parser-policy enforcement.
- Fixed M4 Pack snapshot persistence after M7 so declared evaluation suites populate the mandatory `created_by` audit field; real `equipment-rca-pack@1.0.0` installation now reaches `ACTIVE` in an isolated tenant.
- Fixed M5 nested SQL row serialization, Workflow actor propagation, restricted-JSON normalization, Source locator normalization, Wiki/entity response metadata, idempotent recompile behavior and stale local build-version configuration exposed by real E2E/runtime checks.
- Fixed M4 workflow projection UUID serialization and made Schema validation reuse the immutable composition report produced by Pack composition instead of violating its uniqueness/append-only boundary.
- Closed the M3 local P0 through the real RustFS→ClamAV→credentialed coordinator→credential-free parser sandbox→Temporal→PostgreSQL→API/Web chain; corrected the full EICAR fixture, upload response filtering, SQLAlchemy nested-row serialization, sequential batch rollup and M3 compatibility checks exposed by that E2E.
- Added an independent Temporal SDK time-skipping CI gate, fixed test Activity payload annotations and closed the official test-server initialization condition locally and remotely.
- Scoped the GitHub `runner` context to step-level environment, installed locked Compose verification dependencies and made the M1 regression verifier accept the current M2 deployment.
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

- M2 v1 Workflow Activities remain explicit historical kernel Stubs. No real OCR Provider, external LLM adapter, M8 GridCrew intake/Connector execution or M9 automatic RCA functionality is implemented.
