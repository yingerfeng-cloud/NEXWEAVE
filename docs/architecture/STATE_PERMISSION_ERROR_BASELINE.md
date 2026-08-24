# M0 State, Permission and Error Contract

> Status: Accepted. This document freezes names and cross-cutting semantics; later Milestones implement and test the corresponding business transitions.

## State vocabulary

| Aggregate | States | Terminal / immutable rule |
|---|---|---|
| Source | `REGISTERED`, `ACTIVE`, `REVOKED` | revoke never deletes SourceVersion |
| SourceVersion | `STORED`, `PARSING`, `PARTIAL`, `PARSED`, `FAILED`, `SUPERSEDED` | stored Raw bytes/checksum are immutable |
| Review | `OPEN`, `CLAIMED`, `CHANGES_REQUESTED`, `APPROVED`, `REJECTED`, `CANCELLED` | actions are append-only; approval cannot be rewritten |
| Release | `DRAFT`, `VALIDATING`, `READY_FOR_APPROVAL`, `APPROVED`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `DEPRECATED` | `PUBLISHED` manifest is immutable; deprecation is a new fact |
| SourceAnchor | `VALID`, `STALE`, `UNRESOLVED`, `REVOKED` | historical locator is not rewritten |
| Evidence role | `SUPPORTS`, `OPPOSES`, `CONTEXT` | role is distinct from confidence/similarity |

Transitions occur only through application commands or authorized Temporal Update/Signal handlers. Database jobs, UI state and projection repair cannot advance the authoritative state independently. Illegal transitions return `STATE_TRANSITION_NOT_ALLOWED` and write an audit outcome.

## Base roles and actions

| Role | Baseline actions | Explicit restrictions |
|---|---|---|
| `platform_admin` | platform policy, tenant lifecycle | no automatic knowledge approval |
| `tenant_admin` | tenant identity and spaces | cannot bypass classification or Release rules |
| `space_admin` | members and space policy | no implicit publisher/reviewer privilege |
| `knowledge_engineer` | draft Source/Schema/Compile/Page work | cannot approve own high-risk output |
| `reviewer` | review and evidence decisions | only assigned scope; separation rules apply |
| `publisher` | candidate approval/publish/pointer switch | cannot edit immutable Release |
| `consumer` | fixed-Release query/read | no draft access by default |
| `auditor` | audit/reproducibility read | no mutation |
| `service` | explicitly granted API scopes | no role inheritance from a human owner |

The permission decision is `role actions ∩ tenant/space membership ∩ object state ∩ classification clearance ∩ separation-of-duty policy`. Missing facts mean deny. Hiding a button is not authorization.

## Stable error codes

All public HTTP errors use `application/problem+json` and the JSON Schema at `packages/contracts/schemas/problem.schema.json`.

| Code | Typical status | Meaning / retry rule |
|---|---:|---|
| `VALIDATION_ERROR` | 422 | request does not match contract; fix input |
| `AUTHENTICATION_REQUIRED` | 401 | missing/invalid verified identity |
| `ACCESS_DENIED` | 403 | policy, tenant, space or classification denied; do not retry unchanged |
| `RESOURCE_NOT_FOUND` | 404 | absent or hidden to prevent enumeration |
| `VERSION_CONFLICT` | 409 | business version conflict; reread resource |
| `PRECONDITION_FAILED` | 412 | ETag/If-Match failed; reread resource |
| `STATE_TRANSITION_NOT_ALLOWED` | 409 | command invalid for current state |
| `IDEMPOTENCY_KEY_REUSED` | 409 | same key used with different request hash |
| `SEMANTIC_POLICY_FAILED` | 422 | Schema/Evidence/Release gate failed |
| `RATE_LIMITED` | 429 | retry only after server guidance |
| `DEPENDENCY_UNAVAILABLE` | 503 | transient provider/workflow failure; retry policy applies |
| `INTERNAL_ERROR` | 500 | opaque detail and trace ID; never expose stack/secrets |

`detail` is safe human-readable context and may change; integrations branch only on `code` and HTTP status. Field issues use JSON Pointer locations.

## Data-classification routing

| Classification | Default audience | External model |
|---|---|---|
| `PUBLIC` | authenticated or approved public channel | policy may allow |
| `INTERNAL` | tenant members | only approved provider/profile |
| `CONFIDENTIAL` | explicit space/object clearance | normally private/approved route; audit required |
| `HIGHLY_RESTRICTED` | explicit least-privilege clearance | forbidden for externally hosted model |

Export, event payload, logs, traces, cache and Citation visibility inherit the highest relevant classification; lowering classification requires an auditable authorized decision.
