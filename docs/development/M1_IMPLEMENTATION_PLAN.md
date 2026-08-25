# NEXWEAVE M1 Implementation Plan

> Status: IMPLEMENTED; pending user acceptance. User formally dispatched M1 on 2026-08-24. This plan is subordinate to the approved M1 task book and does not authorize M2 work.

| Workstream | M1 outcome | Requirements | Verification |
|---|---|---|---|
| Identity | Local development provider, production OIDC adapter boundary, user/service principals and audience validation | NXW-ADMIN-001, NXW-NFR-SEC-001 | token, expiry, audience, disabled identity and negative tests |
| Authorization | Default-deny RBAC+ABAC, tenant/space/classification checks, denial audit | NXW-SPACE-001, NXW-NFR-SEC-001 | cross-tenant/cross-space/revocation/classification matrix |
| Workspace | Real create/read/edit/archive and member grant/revoke APIs with idempotency and ETag | NXW-SPACE-001, NXW-SPACE-002 | unit/API/PostgreSQL/Web E2E |
| Governance objects | ModelProfile, PromptVersion, ConnectorDefinition, configuration and audit query | NXW-ADMIN-001, NXW-NFR-SEC-002/003 | contract/API/secret-reference checks |
| Object foundation | ObjectStoragePort, RustFS adapter, controlled upload, checksum, conditional write, scan gate and authorized download | NXW-NFR-SEC-003, M1 task §5 | real RustFS integration and overwrite denial |
| Audit and events | Append-only audit, transactional Outbox and M1 event schemas | NXW-NFR-AUD-001, NXW-ADMIN-001 | DB transaction/append-only/contract tests |
| Observability | W3C trace propagation, structured logs/metrics and diagnostics | M1 task §5 | API/DB/object trace correlation tests |
| Web | Auth state, 16 deep-link routes, guards, space switcher, space/member/admin real API views | NXW-DASH-001, NXW-SPACE-001/002, NXW-ADMIN-001 | component/routing/error/recovery/E2E |

## Explicit exclusions

- No SourceDocument/SourceVersion, parser or SourceIngestion Workflow implementation;
- no Schema, Compile, Wiki, Evidence, Review, Release, Query or GridCrew business implementation;
- no external Connector execution and no direct model invocation;
- no claim that the M1 scan stub is a production malware scanner.
