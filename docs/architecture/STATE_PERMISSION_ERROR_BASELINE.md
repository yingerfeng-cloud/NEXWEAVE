# M5-governance-calibrated State, Permission and Error Contract

> Status: M1—M7 are formally accepted; ADR-0026 M7 Quality/Release/Query/Graph states, actions and stable errors are implemented and locally technically accepted. M8+ integration state is not implemented.

## State vocabulary

| Aggregate | States | Terminal / immutable rule |
|---|---|---|
| SourceDocument | `REGISTERED`, `ACTIVE`, `ARCHIVED` | archive never deletes SourceVersion; invalidation is an append-only fact; no M3 physical delete |
| SourceVersion | `STORED`, `PARSING`, `PARTIAL`, `PARSED`, `FAILED`, `SUPERSEDED` | stored Raw bytes/checksum are immutable |
| SourceInvalidation | `RECORDED` | append-only validity fact; does not overwrite parse status or Raw |
| ImportBatch | `CREATED`, `UPLOADING`, `PROCESSING`, `PARTIAL`, `SUCCEEDED`, `FAILED`, `CANCELED` | item results are independent; batch failure does not roll back successes |
| ParseJob | `CREATED`, `QUEUED`, `RUNNING`, `PARTIAL_FAILED`, `FAILED`, `SUCCEEDED`, `CANCELED` | each reparse is a new job; retry keeps fixed input/config |
| Review | `OPEN`, `CLAIMED`, `CHANGES_REQUESTED`, `APPROVED`, `REJECTED`, `CANCELLED` | actions are append-only; approval cannot be rewritten |
| Release | `DRAFT`, `VALIDATING`, `READY_FOR_APPROVAL`, `APPROVED`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `DEPRECATED` | `PUBLISHED` manifest is immutable; deprecation is a new fact |
| SourceAnchor | `VALID`, `STALE`, `UNRESOLVED`, `REVOKED` | historical locator is not rewritten |
| Evidence role | `SUPPORTS`, `OPPOSES`, `CONTEXT` | role is distinct from confidence/similarity |
| KnowledgeSpace | `ACTIVE`, `ARCHIVED` | archive is soft and M1 exposes no restore or physical delete |
| SpaceMember | `ACTIVE`, `REVOKED` | revoke retains the policy fact and denies subsequent access |
| UploadSession | `INITIATED`, `UPLOADING`, `COMPLETING`, `COMPLETED`, `ABORTED`, `EXPIRED` | terminal sessions cannot accept new bytes |
| Object scan | `PENDING`, `CLEAN`, `INFECTED`, `FAILED` | only `CLEAN` bytes can be downloaded |
| Governance | `DRAFT`, `ACTIVE`, `DISABLED`, `DEPRECATED` | PromptVersion is append-only; M1 does not execute models/connectors |
| SchemaVersion | `DRAFT`, `TESTING`, `PUBLISHED`, `DEPRECATED` | PUBLISHED content/composition checksum/Pack inputs are immutable; R1 has no separate OntologyVersion state |
| DomainPackVersion | `DRAFT`, `VALIDATED`, `PUBLISHED`, `REVOKED`, `DEPRECATED` | published artifact/checksum is immutable; revocation does not delete history |
| Installation | `PLANNED`, `INSTALLING`, `ACTIVE`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK`, `DISABLED` | ACTIVE means exact PackVersion was installed and candidate/effective Schema refs recorded; it does not itself publish Schema |
| CompileJob | `CREATED`, `QUEUED`, `RUNNING`, `PAUSED`, `PARTIAL_FAILED`, `FAILED`, `SUCCEEDED`, `CANCELED` | fixed inputs cannot change; retries/recompile create a new job instead of rewriting terminal history |
| WikiPage | `DRAFT`, `IN_REVIEW`, `APPROVED`, `RELEASED`, `DEPRECATED` | M5 creates/edits DRAFT only; stable identity points to append-only current version |
| WikiPageVersion | `AI_DRAFT`, `EDITING`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `RELEASED`, `DEPRECATED` | content is immutable; M5 creates `AI_DRAFT`/`EDITING` only and does not approve or release |
| WorkflowTask | `CREATED`, `STARTING`, `RUNNING`, `PAUSED`, `WAITING`, `WAITING_INPUT`, `CANCELLING`, `COMPENSATING`, `CANCELLED`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `REJECTED` | Temporal advances execution; terminal tasks do not accept control except FAILED/TIMED_OUT retry |
| WorkflowStep | `PENDING`, `RUNNING`, `RETRYING`, `PAUSED`, `WAITING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `COMPENSATED` | projection is repairable; Event history is append-only |

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

M1 concretely grants only the actions declared in `packages/domain/src/nexweave_domain/access.py`. Service identities receive no action from the tenant `service` role alone: they require `nexweave-api` audience and explicit active space membership/space role. Platform/tenant admins can inspect tenant facts, but classification clearance and archived-resource rules still constrain the result. Every denied tenant/space decision is appended to AuditLog with the request trace ID.

M2 adds `workflow.create`, `workflow.read`, `workflow.control`, `workflow.review` and `workflow.reconcile`. The API intersects these role actions with active membership and the authoritative Workflow status before returning `allowed_actions`; `If-Match` and command idempotency are mandatory for mutation. A Web button, database projection value or client-supplied actor never grants a command.

M3 implements actions `source.upload`, `source.read`, `source.download`, `source.parse`, `source.invalidate` and `source.archive`; they are locally verified and remain subject to active tenant/space membership, Source state, classification clearance, ETag/idempotency and server-side reauthorization. Source business endpoints start/control the v2 Workflow; access to generic M2 task commands alone does not grant Source mutation.

M4 implements `schema.read`, `schema.edit`, `schema.validate`, `schema.publish`, `pack.read`, `pack.install` and `pack.rollback`. Editing terms, hierarchy or mappings requires `schema.edit`; composition/impact preview requires `schema.validate`; publishing a semantic snapshot requires `schema.publish` plus configured approval/separation. Pack install authority never implies Schema publish authority.

M5 implements `compile.create`, `compile.read`, `knowledge.read`, `page.read`, `page.edit` and `page.comment`. Knowledge engineers can create/read Compile jobs and edit/comment on governed drafts; consumers receive no draft Compile/Entity/Wiki access. Page editing requires the current version, strong ETag and idempotency key, and can change only protected sections/properties/title; generated sections remain compile-owned. These permissions do not grant M6 review/conflict resolution or M7 publish authority.

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
| `INVALID_CURSOR` | 400 | opaque cursor is malformed or its continuation anchor is unavailable |
| `SEMANTIC_POLICY_FAILED` | 422 | Schema/Evidence/Release gate failed |
| `SEMANTIC_MODEL_INVALID` | 422 | stable key/reference/hierarchy/term/mapping contract failed; fix declaration |
| `SEMANTIC_MAPPING_AMBIGUOUS` | 409 | mapping or term resolves to multiple incompatible semantic targets; human resolution required |
| `SCHEMA_BREAKING_CHANGE` | 409 | direct publish blocked pending impact report, migration plan and approval |
| `PACK_DEPENDENCY_CONFLICT` | 409 | dependency range is missing, cyclic, ambiguous or incompatible |
| `PACK_COMPOSITION_CONFLICT` | 409 | duplicate key, inherited constraint, endpoint or mapping definitions cannot be deterministically composed |
| `RATE_LIMITED` | 429 | retry only after server guidance |
| `DEPENDENCY_UNAVAILABLE` | 503 | transient provider/workflow failure; retry policy applies |
| `BUSINESS_KEY_CONFLICT` | 409 | stable workflow business key already exists with a different creation payload |
| `WORKFLOW_COMMAND_REJECTED` | 409 | command is not valid for the current Workflow type/status |
| `WORKFLOW_DEPENDENCY_UNAVAILABLE` | 503 | Temporal operation unavailable; retry only with the same idempotency key |
| `SOURCE_TYPE_UNSUPPORTED` | 415 | extension/MIME/magic or approved whitelist rejects the file; do not retry unchanged |
| `SOURCE_CHECKSUM_MISMATCH` | 422 | server-verified Raw differs from declaration; do not register/parse unchanged |
| `SOURCE_MALWARE_DETECTED` | 422 | scanner detected disallowed content; quarantine and do not retry unchanged |
| `SOURCE_SECURITY_POLICY_FAILED` | 422 | macro/active content/decompression/resource policy failed |
| `PARSER_CAPABILITY_UNAVAILABLE` | 422 | no approved Parser/OCR capability for the fixed input/config |
| `PARSER_RESOURCE_LIMIT_EXCEEDED` | 422 | parser budget exceeded; policy/config change requires reparse, not blind retry |
| `OCR_REQUIRED` | 422 | scanned/no-text unit requires a real OCR Provider; may be a partial-result unit |
| `PARSE_RESULT_INVALID` | 500 | Provider result failed the trusted document contract; do not persist as success |
| `ANCHOR_UNRESOLVED` | 409 | locator cannot be verified for the selected parse result |
| `COMPILE_INPUT_UNAVAILABLE` | 422 | fixed Schema/Prompt/Model/Source input cannot be resolved in the authorized tenant/space |
| `COMPILE_SOURCE_NOT_READY` | 422 | SourceVersion lacks an eligible successful parse result/anchor set |
| `COMPILE_SCHEMA_NOT_PUBLISHED` | 422 | only a PUBLISHED SchemaVersion may be compiled |
| `COMPILE_PROMPT_UNAVAILABLE` | 422 | fixed PromptVersion is not active/available |
| `COMPILE_MODEL_UNAVAILABLE` | 422 | fixed ModelProfile is not active/available |
| `MODEL_CLASSIFICATION_DENIED` | 403 | model profile classification ceiling is below an input classification |
| `MODEL_EGRESS_DENIED` | 403 | data egress policy forbids this model route |
| `MODEL_PROVIDER_UNAVAILABLE` | 503 | configured external provider is not available; retry only under the fixed profile or create a new job |
| `WIKI_VERSION_NOT_CURRENT` | 409 | edit target is not the current draft version; reload before retrying |
| `EVALUATION_SCHEMA_NOT_PUBLISHED` | 409 | suite does not bind a published SchemaVersion in the same space |
| `RELEASE_INPUT_UNAVAILABLE` | 404 | one or more fixed candidate inputs cannot be resolved in scope |
| `RELEASE_EVIDENCE_REQUIRED` | 409 | selected Claim/Relation lacks accepted Evidence with VALID Anchor |
| `RELEASE_DUTY_SEPARATION` | 409 | candidate creator attempted to approve publication |
| `RELEASE_NOT_READY` | 409 | quality/conflict/lint gate has not reached approval-ready state |
| `RELEASE_APPROVAL_REQUIRED` | 409 | matching audited Publisher approval is absent |
| `PRECONDITION_FAILED` | 412 | strong pointer ETag is stale or malformed |
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
