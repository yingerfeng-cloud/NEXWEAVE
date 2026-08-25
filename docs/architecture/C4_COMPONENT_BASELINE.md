# M2 C4 Architecture Baseline

> Status: M0 context/container boundaries remain Accepted; ADR-0019 adds M1 platform components and ADR-0020 adds the M2 reliable Workflow kernel, task projection and task center without changing the frozen container topology.

## Level 1 — System context

```mermaid
flowchart LR
  Expert[Knowledge engineer / expert] --> Web[NEXWEAVE Web]
  Consumer[Business consumer / auditor] --> Web
  Web --> API[NEXWEAVE public API]
  GridCrew[GridCrew] -->|fixed Release API / SDK / event| API
  Source[Enterprise source systems] -->|Connector boundary| API
  API --> Core[NEXWEAVE trusted knowledge platform]
  Core --> Provider[OIDC / Model Gateway / storage / parser providers]
```

NEXWEAVE owns knowledge ingestion, compilation, evidence, review, evaluation, immutable release and trusted query. It does not own GridCrew task orchestration or directly share GridCrew business state.

## Level 2 — Containers

```mermaid
flowchart TB
  Browser[Browser] --> Web[React / TypeScript Web]
  Web --> API[FastAPI modular-monolith API]
  Integration[Connector / GridCrew / SDK] --> API
  API --> PostgreSQL[(PostgreSQL + pgvector)]
  API --> RustFS[(RustFS / S3 Raw objects)]
  API --> Redis[(Redis cache / coordination)]
  API --> Temporal[Temporal]
  Temporal --> Workers[Independent Python Workers]
  Workers --> Ports[Model / Parser / Search / Object / Connector Ports]
  Workers --> PostgreSQL
  Workers --> RustFS
  PostgreSQL --> Projections[Rebuildable FTS / vector / relation projections]
```

M2 runs eight services through Compose: the M0 health Worker remains isolated and `worker-kernel` registers seven versioned Workflow definitions on a dedicated Workflow queue plus Activities on a dedicated Activity queue. The API exposes authenticated task control and PostgreSQL projection queries; future Model/Parser/Search/Connector ports remain boundaries, not claims of implemented adapters.

## Level 3 — API components

```mermaid
flowchart LR
  Routes[HTTP adapter] --> Platform[Platform health/version]
  Routes --> Identity[Identity and authorization application boundary]
  Routes --> Workspace[Workspace and membership application boundary]
  Routes --> Governance[Governance configuration boundary]
  Routes --> Objects[Controlled object application boundary]
  Routes --> Tasks[Workflow task and reconciliation boundary]
  Routes --> Error[Problem Details mapper]
  Identity --> IdP[Local / OIDC IdentityProvider adapters]
  Workspace --> Repo[PostgreSQL Repository]
  Governance --> Repo
  Objects --> ObjectPort[ObjectStoragePort / MalwareScannerPort]
  Tasks --> WorkflowPort[WorkflowGatewayPort]
  WorkflowPort --> TemporalAdapter[Temporal client adapter]
  Tasks --> Repo
  ObjectPort --> S3[RustFS S3 adapter]
  Repo --> Audit[Audit + Outbox + idempotency transaction facts]
  Platform --> Probe[Infrastructure health port]
  Probe --> PG[PostgreSQL adapter]
  Probe --> R[Redis adapter]
  Probe --> O[Object storage health adapter]
  Probe --> T[Temporal reachability adapter]
  Routes --> Contracts[Public Pydantic / JSON Schema contracts]
  Contracts --> Domain[Pure domain vocabulary / UUIDv7]
```

Business modules follow `HTTP/Worker adapter → application Port/use-case boundary → domain`. ORM, FastAPI, Temporal and provider SDKs cannot enter `packages/domain`, `packages/contracts` or `packages/application`; an automated architecture test enforces the rule.

## Level 3 — Worker components

```mermaid
flowchart LR
  Temporal[Temporal server] --> Worker[Worker host]
  Worker --> Workflow[Deterministic Workflow definitions]
  Worker --> Activities[Retryable idempotent Activities]
  Activities --> Ports[Application ports]
  Ports --> Adapters[DB / object / model / connector adapters]
```

M0 retains `PlatformHealthWorkflow`. M2 adds seven explicit deterministic kernel Workflows. They use Temporal Update/Signal/query and call only named Activities; projection, step and compensation I/O is isolated in Activities. M2 Activity outcomes are Stubs and do not create M3+ business aggregates.

## Source tree mapping

| Boundary | Location | M2 content |
|---|---|---|
| Web adapter | `apps/web` | authenticated shell, platform pages and real M2 task center |
| API adapters | `apps/api` | M1 platform adapters plus Temporal gateway, task repository/routes and reconcile |
| Application boundary | `packages/application` | M1 ports plus vendor-neutral `WorkflowGatewayPort` |
| Pure domain | `packages/domain` | platform vocabulary plus Workflow types/states/commands/stable IDs |
| Public contracts | `packages/contracts` | M1/M2 Pydantic, JSON Schema, event payload and OpenAPI snapshots |
| Client SDK | `packages/sdk` | typed Python/TypeScript platform and task API clients |
| Workflow hosts | `workers/health`, `workers/kernel` | deterministic health plus seven M2 kernel Workflows/Activities |
| Persistence evolution | `migrations` | M0/M1 foundations plus `0003_m2_temporal_kernel` |
| Local deployment | `compose.yaml`, Dockerfiles | PostgreSQL/Redis/RustFS/Temporal/API/two Workers/Web |

## Evolution constraints

- Split a module into a service only after stable Port/contract evidence exists; database table ownership and outbox behavior must remain explicit.
- Search/vector/graph stores are projections, not business authority.
- Provider reuse with GridCrew never grants shared business database or implicit availability authority.
- Production Kubernetes, HA, DR and domestic-platform certification are later-stage deployment decisions, not M0 claims.
