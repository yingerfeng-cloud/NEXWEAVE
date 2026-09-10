# API Contract Baseline

> 公共前缀：`/api/v1`。M1—M7 端点已实现并正式验收；M7 Quality/Release/Graph/Query API 已通过本地契约与隔离真实 E2E 技术验收。远程 CI 未在无提交授权下伪称执行。
> 所有写请求必须包含授权、审计、乐观锁/前置条件和幂等策略；异步请求返回业务对象 ID 与 Workflow ID。

## M0 已实现的平台端点

| 方法与路径 | 语义 | 公开契约 |
|---|---|---|
| `GET /health/live` | 进程存活，不代替依赖就绪 | OpenAPI snapshot |
| `GET /health/ready` | PostgreSQL、Redis、RustFS/S3 对象存储、Temporal 实际探测 | `ReadinessReport` |
| `GET /version` | 产品/Release/Milestone/构建版本 | OpenAPI snapshot |
| `GET /config/diagnostics` | 只返回脱敏配置诊断 | OpenAPI snapshot |

以上是工程健康面，不是知识业务能力。已实现路径由 `packages/contracts/openapi/nexweave-platform-v1.openapi.json` 锁定并在 CI 中防漂移。

## M1 已实现端点

| 资源 | 路径 | 权限/并发语义 |
|---|---|---|
| 认证 | `POST /auth/dev/session`, `GET /auth/me` | Bearer；开发签发端点在非 development 环境不可用 |
| 身份 | `GET /roles`, `GET/POST /users`, `GET /organizations`, `GET/POST /service-identities` | `identity.manage`；创建使用 `Idempotency-Key` |
| 空间 | `GET/POST /spaces`, `GET/PATCH /spaces/{id}`, `POST /spaces/{id}/archive` | tenant/space RBAC+ABAC；写入使用幂等键，更新/归档使用强 `If-Match` |
| 成员 | `GET /spaces/{id}/members`, `PUT/DELETE /spaces/{id}/members/{subject_id}` | `member.read/grant/revoke`；撤销保留事实并即时失效 |
| 治理 | `GET/POST /model-profiles`, `GET/POST /prompt-versions`, `GET/POST /connector-definitions`, `GET /audit-logs` | 管理权限；Secret 仅引用；PromptVersion 追加式 |
| 对象 | `POST /spaces/{id}/object-uploads`, `PUT /object-uploads/{id}/content`, `GET /objects/{id}`, `GET /objects/{id}/content` | 空间/密级授权、条件创建、服务端 checksum、扫描门禁、下载重新授权 |

所有 M1 列表支持 `limit`（1—100）和 opaque `cursor`，响应包含 `items` 与可空 `next_cursor`；顺序由仓储显式固定。M1 的 `ManagedObject` 是基础设施验证对象，不是 SourceVersion，也不能进入 Evidence/Release。

## M2 已实现端点

| 方法与路径 | 语义 | 权限/并发语义 |
|---|---|---|
| `POST /spaces/{space_id}/workflow-tasks` | 以稳定 business key 创建并启动七类内核任务 | `workflow.create`；`Idempotency-Key`；返回业务任务 ID、Workflow ID、Run ID 与 `Location` |
| `GET /spaces/{space_id}/workflow-tasks` | 查询 PostgreSQL 任务投影 | `workflow.read`；稳定游标，可按类型/状态过滤；标记投影来源 |
| `GET /workflow-tasks/{task_id}` | 查询任务、步骤、追加日志和当前允许动作 | `workflow.read`；强 ETag；服务端按角色和真实状态过滤动作 |
| `POST /workflow-tasks/{task_id}/commands` | pause/resume/cancel/claim/request/provide/approve/reject/retry | `workflow.control` 或 `workflow.review`；`Idempotency-Key` + `If-Match`；Temporal Update 为执行权威 |
| `POST /workflow-tasks/{task_id}/reconcile` | 比对 Temporal 查询状态并修复数据库投影 | `workflow.reconcile`；记录审计/Outbox；不从数据库反向推进 Workflow |

任务创建是通用 M2 内核入口，不替代 M3+ 的 Source/Compile/Review/Release 等业务命令。`input_refs` 只保存有界引用，不能承载文件正文、凭据或领域业务对象。

## 通用错误语义

| 状态 | 语义 |
|---|---|
| 400 | 契约/业务输入无效，返回稳定错误码和字段问题 |
| 401 | 未认证或令牌无效 |
| 403 | 权限、密级、租户或空间范围拒绝，并写审计 |
| 404 | 对调用者不可见或不存在；防止越权枚举 |
| 409 | 状态冲突、版本冲突、幂等负载冲突或唯一约束冲突 |
| 412 | ETag/前置条件失败 |
| 422 | Schema、Evidence、发布门禁等语义校验失败 |
| 429 | 配额/速率限制 |
| 503 | Provider/Workflow 暂不可用，可返回重试提示 |

列表接口统一使用稳定游标分页、显式排序和过滤。错误采用 RFC 9457 风格 `application/problem+json`，稳定字段为 `type`, `title`, `status`, `detail`, `instance`, `code`, `trace_id`, `errors`, `extensions`；调用方只能基于 `code`/HTTP 状态分支。

## 资源清单

| 方法与路径 | 调用方 / 权限 | 幂等 | 主要输入输出 | 模式 | 阶段 |
|---|---|---|---|---|---|
| `POST /spaces` | 平台/租户管理员；`space.create` | `Idempotency-Key` | SpaceCreate → KnowledgeSpace | 同步或初始化异步 | M1 |
| `GET /spaces/{space_id}` | 空间成员；`space.read` | GET | KnowledgeSpace + etag | 同步 | M1 |
| `PATCH /spaces/{space_id}` | 空间管理员；`space.edit` | `If-Match` + request key | SpacePatch → new version | 同步 | M1 |
| `POST /spaces/{space_id}/archive` | 空间管理员；`space.archive` | command key | ArchiveCommand → state | 同步 | M1 |
| `PUT /spaces/{space_id}/members/{subject_id}` | 空间管理员；`member.grant` | resource PUT | MembershipPolicy → SpaceMember | 同步 | M1 |
| `DELETE /spaces/{space_id}/members/{subject_id}` | 空间管理员；`member.revoke` | resource DELETE | revoke result | 同步 | M1 |
| `POST /spaces/{space_id}/sources/uploads` | 知识工程师；`source.upload` | upload session key | metadata → upload session | 同步 | M3 |
| `POST /spaces/{space_id}/source-import-batches` | 知识工程师；`source.upload` | batch key | metadata → ImportBatch | 同步 | M3 |
| `PUT /sources/uploads/{upload_id}/content` | 上传者；`source.upload` | conditional session write | Raw bytes → upload state | 同步/受控 multipart | M3 |
| `POST /sources/uploads/{upload_id}/complete` | 上传者；`source.upload` | checksum + key | checksum/parts → SourceVersion + workflow | 异步 | M3 |
| `POST /sources/uploads/{upload_id}/abort` | 上传者；`source.upload` | command key | 未完成会话 → ABORTED/批次单项终态 | 同步 | M3 |
| `GET /spaces/{space_id}/sources` | `source.read` + 密级 | GET | SourceDocument page | 同步 | M3 |
| `GET /sources/{source_id}` | `source.read` + 密级 | GET | metadata/version chain/etag | 同步 | M3 |
| `POST /sources/{source_id}/archive` | `source.archive` | command key + etag | archive result | 同步 | M3 |
| `GET /sources/{source_id}/versions/{version_id}` | `source.read` + 密级 | GET | SourceVersion metadata | 同步 | M3 |
| `GET /source-versions/{id}/content` | `source.download` + 密级 | GET | 受控下载/流 | 同步 | M3 |
| `GET /source-versions/{id}/preview?anchor_id=...` | `source.read` + 密级 | GET | sanitized preview + per-locator status | 同步 | M3 |
| `GET /source-versions/{id}/segments` | `source.read` + 密级 | GET | active/selected ParseJob segments | 同步 | M3 |
| `POST /source-versions/{id}/parse` | `source.parse` | source+parser+config key + etag | ReparseCommand → new ParseJob/v2 Workflow | 异步 | M3 |
| `GET /parse-jobs/{id}` | `source.read` + 密级 | GET | ParseJob/steps/failure units/config/result | 同步 | M3 |
| `POST /parse-jobs/{id}/retry` | `source.parse` | command key + etag | same-config retry → same business job/new Run if closed | 异步 | M3 |
| `POST /parse-jobs/{id}/cancel` | `source.parse` | command key + etag | 未终态 ParseJob → CANCELED | 异步 | M3 |
| `POST /source-versions/{id}/invalidate` | `source.invalidate` | command key | reason → new state | 同步 | M3 |
| `POST /spaces/{space_id}/schemas` | `schema.edit` | key | SchemaCreate → definition/version | 同步 | M4 |
| `GET /schemas/{schema_id}/versions/{version}` | `schema.read` | GET | SchemaVersion | 同步 | M4 |
| `GET /schemas/{schema_id}/versions/{version}/semantic-model` | `schema.read` | GET | normalized types/properties/hierarchy/relations/terms/mappings + composition checksum | 同步；SchemaVersion 的只读逻辑视图 | M4 |
| `POST /schemas/{schema_id}/compose` | `schema.edit` | command key | exact PackVersion refs + local declarations → SchemaCompositionReport/new draft snapshot | 同步；不得发布 | M4 |
| `GET /schema-composition-reports/{report_id}` | `schema.read` | GET | inputs/conflicts/compatibility/impact/checksum | 同步 | M4 |
| `POST /schemas/{schema_id}/versions/{version}/validate` | `schema.validate` | content hash | Schema draft → compatibility report | 同步 | M4 |
| `POST /schemas/{schema_id}/versions/{version}/publish` | `schema.publish` | command key + etag | validated draft → published SchemaVersion | 同步；职责分离由授权身份验证 | M4 |
| `POST /spaces/{space_id}/compile-jobs` | `compile.create` | scope+schema+config key | CompileRequest → CompileJob/workflow | 异步 | M5 |
| `GET /spaces/{space_id}/compile-jobs` | `compile.read` | GET | CompileJob list | 同步 | M5 |
| `GET /compile-jobs/{job_id}` | `compile.read` | GET | job, fixed inputs, steps, errors, cost/result summary | 同步 | M2/M5 |
| `GET /spaces/{space_id}/wiki/pages` | `page.read` | GET | stable Page identities + current draft refs | 同步 | M5 |
| `GET /wiki/pages/{page_id}` | `page.read` | GET | current draft, links/backlinks, safe Evidence candidate metadata, comments/follow state | 同步 | M5 |
| `GET /wiki/pages/{page_id}/versions` | `page.read` | GET | append-only WikiPageVersion list | 同步 | M5 |
| `GET /wiki/pages/{page_id}/versions/{version_id}` | `page.read` | GET | fixed WikiPageVersion | 同步 | M5 |
| `PATCH /wiki/pages/{page_id}/drafts/{version_id}` | `page.edit` | `If-Match` | edits/diff → new page version | 同步 | M5 |
| `GET /wiki/pages/{page_id}/diff` | `page.read` | GET | version diff | 同步 | M5 |
| `POST /wiki/pages/{page_id}/comments` | `page.comment` | append-only | comment body → WikiComment | 同步 | M5 |
| `PUT/DELETE /wiki/pages/{page_id}/follow` | `page.read` | resource PUT/DELETE | current actor follow state | 同步 | M5 |
| `GET /spaces/{space_id}/entities` | `knowledge.read` | GET | entities by schema/release | 同步 | M5/M7 |
| `GET /spaces/{space_id}/claims` | `claim.read` | GET | approved Claim with scope/status/provenance | 同步 | M6 |
| `GET /claims/{claim_id}/evidence` | `claim.read` + source ACL | GET | accepted Evidence with SourceAnchor metadata | 同步 | M6 |
| `GET /spaces/{space_id}/conflicts` | `conflict.read` | GET | conflict queue | 同步 | M6 |
| `POST /spaces/{space_id}/conflicts/detect` | `conflict.resolve` | command key | M5 candidates → M6 cluster cases; preserves originals | 同步 | M6 |
| `POST /conflicts/{id}/decisions` | `conflict.resolve` | command key | append resolution/evidence snapshot/reason → state | 同步 + audit | M6 |
| `POST /spaces/{space_id}/review-policies` | `review.policy.manage` | command key | versioned risk/stage/timeout/batch policy | 同步 | M6 |
| `GET /spaces/{space_id}/review-cases` | `review.read` | GET | review queue and Temporal-linked tasks | 同步 | M6 |
| `POST /spaces/{space_id}/review-cases` | `review.create` | command key | candidate + policy → ReviewCase/HumanReview v2 | 异步 | M6 |
| `POST /review-cases/{case_id}/tasks/{task_id}/actions` | `review.act` | action key | accept/modify/reject/request-evidence/transfer | Workflow signal + audit | M6 |
| `POST /spaces/{space_id}/evaluations/runs` | `evaluation.run` | suite+target+config key | EvaluationRequest → run/workflow | 异步 | M7 |
| `GET /evaluations/runs/{id}` | `evaluation.read` | GET | metrics/errors/config versions | 同步 | M7 |
| `POST /spaces/{space_id}/release-candidates` | `release.create` | content manifest key | scope/version → candidate | 异步 | M7 |
| `POST /release-candidates/{id}/publish` | `release.publish` + approval | command key + etag | publish command → workflow | 异步 | M7 |
| `GET /spaces/{space_id}/releases` | `release.read` | GET | release history | 同步 | M7 |
| `GET /releases/{release_id}` | `release.read` | GET | immutable manifest/metadata | 同步 | M7 |
| `GET /releases/{release_id}/export` | `release.read` | GET | immutable JSON/Markdown release export | 同步 | M7 |
| `POST /releases/{release_id}/projections/rebuild` | `release.publish` | command key | rebuild FTS/vector projection from Release | 同步 + audit | M7 |
| `GET /spaces/{space_id}/release-pointer` | `release.read` | GET | channel pointer/version | 同步 | M7 |
| `POST /spaces/{space_id}/release-pointer` | `release.rollback/switch` | command key + etag | target release → pointer | 异步 | M7 |
| `GET /releases/{release_id}/graph/traverse` | `query.release` | GET/query hash | nodes/edges/evidence refs | 同步 | M7 |
| `POST /releases/{release_id}/queries` | `query.release` | client request ID | question/filters → QueryAnswer/Citations | 同步或 async handle | M7 |
| `GET /query-answers/{answer_id}` | answer owner/audit | GET | reproducible answer | 同步 | M7 |
| `GET /domain-packs` | `pack.read` | GET | compatible Pack versions | 同步 | M4 |
| `POST /domain-pack-trust-keys` | `governance.manage` | command key | Ed25519 public trust root | 同步 | M4 |
| `POST /domain-packs` | `governance.manage` | artifact key | signed manifest + declarations → immutable PackVersion | 同步 | M4 |
| `POST /domain-pack-revocations/import` | `governance.manage` | evidence key | signed offline revocation list → revocation facts | 同步接受 | M4 |
| `POST /spaces/{space_id}/domain-pack-installations` | `pack.install` + approval | space+pack version key | InstallRequest → installation/workflow | 异步 | M4 |
| `GET /domain-pack-installations/{id}` | `pack.read` | GET | exact PackVersion/checksum, dependency resolution, candidate/published SchemaVersion, report | 同步 | M4 |
| `POST /spaces/{space_id}/domain-pack-installations/{id}/disable` | `pack.rollback` | command key | active installation → recomposed candidate/workflow | 异步 | M4 |
| `POST /spaces/{space_id}/domain-pack-installations/rollback` | `pack.rollback` | command key | exact historical target → workflow | 异步 | M4 |
| `POST /spaces/{space_id}/connectors` | `connector.manage` | key | config + CredentialRef → Connector | 同步 | M8 |
| `POST /connectors/{id}/sync-runs` | `connector.run` | connector+watermark key | sync request → workflow | 异步 | M8 |
| `GET /connectors/{id}/sync-runs/{run_id}` | `connector.read` | GET | status/errors/watermark | 同步 | M8 |
| `POST /integrations/gridcrew/query` | GridCrew ServiceIdentity; fixed release policy | GridCrew request ID | skill context/question → answer/citations | 同步 | M8 |
| `GET /integrations/gridcrew/releases/{id}/evidence/{eid}` | GridCrew ServiceIdentity + delegated scope | GET | permitted evidence metadata/content | 同步 | M8 |
| `POST /integrations/gridcrew/feedback` | GridCrew ServiceIdentity | task/feedback ID | feedback/case draft → intake workflow | 异步；只入草稿 | M8 |

## M1/M2 契约单一来源与兼容规则

- HTTP 路由/Pydantic 模型导出并提交 OpenAPI 3.1 snapshot；CI 比对实现与 snapshot，更新 snapshot 必须作为公共契约变化评审。
- 跨 HTTP/事件/SDK 的模型以 `packages/contracts` Pydantic 模型为 canonical source，生成并提交 JSON Schema Draft 2020-12；CI 阻断生成物漂移。
- Python/TypeScript SDK 以已提交 OpenAPI/JSON Schema 为权威，M1 提供平台基础，M2 增加任务 create/list/detail/command/reconcile；SDK 不反向修改契约。
- verified OIDC/service identity 提供 actor/tenant claims；路径/资源 space 与 claims 共同校验。客户端自报 header 不授予租户权限。
- 产生副作用的命令使用 `Idempotency-Key`；可变资源写入使用 `If-Match`；列表使用 opaque cursor；异步命令返回 operation/business ID + Workflow ID。
- 同 major 只允许增加可选字段或新路径。删除、改义、收紧枚举和 Release/Evidence/SourceAnchor 语义变化必须 ADR + 新 major/迁移窗口。

M3 实现补充：Source 业务端点已启动/关联 `nexweave.source-ingestion.v2` 与 ParseJob，不要求客户端使用通用 M2 Stub 创建业务结果；v1 路径/历史保持 Replay。M3 错误码、事件、OpenAPI/JSON Schema 和 SDK 已进入 canonical contracts 与生成物门禁并完成本地、远程验证；M3 已于 2026-08-29 正式验收。

M4 语义模型实现补充：公共资源权威是 `/schemas` 与 `/domain-packs`，R1 无 `/ontologies`。`semantic-model` 是不可变 SchemaVersion 的只读表示；compose/validate 固定 PackVersion/checksum 与本地声明并返回确定性 checksum、冲突和影响报告。Pack 安装只生成 DRAFT 候选，不自动发布。上述路径已进入 OpenAPI/JSON Schema/SDK/权限/幂等和本地契约/E2E 门禁。

M5 实现补充：Compile 创建时服务端固定已发布 SchemaVersion/composition checksum、排序后的 SourceVersion/checksum/ParseJob、PromptVersion 与 ModelProfile；运行中不可换参。失败或取消后的人工“重试”创建新的 `RECOMPILE` CompileJob，而非覆盖旧任务。M5 不另行暴露 Compile pause/resume/cancel 业务路由；通用 M2 Stub 控制语义不得冒充 M5 Compile 控制能力。Wiki 编辑以强 ETag 和幂等键创建追加版本，只允许修改保护区/属性，编译生成区不可由编辑接口覆盖。M5 输出全部保持候选态，不提供 M6 审核、冲突解决或正式发布接口。

M6 实现补充：`ClaimCandidate`/`EvidenceCandidate` 仅经 ReviewCase 完整阶段后复制为正式 Claim/Evidence；批准时服务端验证至少一条 `VALID` SourceAnchor Evidence。`nexweave.human-review.v1` 保留历史 Stub，新增 `v2` 等待最终可审计决策。冲突候选显式投影为保留双方快照的 ConflictCase；未决阻断项不能被后续 Release 绕过。

M7 实现补充：EvaluationSuite/Run 固定 Schema、目标、策略与逐题结果；ReleaseCandidate 显式锁定正式对象、Evidence/Anchor、Schema composition、Prompt、Model、Suite 和索引配置。KnowledgeRelease v2 在门禁通过后等待独立 Publisher，再原子固化 Release/Items/投影/Pointer/Outbox。Query 路径必须显式 Release ID，客户端请求 ID 幂等复现回答，检索执行密级、Evidence 与 VALID Anchor 过滤；证据不足返回无 Citation 的拒答。回滚只用强 ETag 移动 Pointer。
