# API Contract Baseline

> 公共前缀：`/api/v1`。M0 已冻结跨域语义；资源表是后续 Milestone 的公共契约目录，不代表业务 API 已实现。  
> 所有写请求必须包含授权、审计、乐观锁/前置条件和幂等策略；异步请求返回业务对象 ID 与 Workflow ID。

## M0 已实现的平台端点

| 方法与路径 | 语义 | 公开契约 |
|---|---|---|
| `GET /health/live` | 进程存活，不代替依赖就绪 | OpenAPI snapshot |
| `GET /health/ready` | PostgreSQL、Redis、RustFS/S3 对象存储、Temporal 实际探测 | `ReadinessReport` |
| `GET /version` | 产品/Release/Milestone/构建版本 | OpenAPI snapshot |
| `GET /config/diagnostics` | 只返回脱敏配置诊断 | OpenAPI snapshot |

以上是工程健康面，不是知识业务能力。已实现路径由 `packages/contracts/openapi/nexweave-platform-v1.openapi.json` 锁定并在 CI 中防漂移。

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
| `POST /sources/uploads/{upload_id}/complete` | 上传者；`source.upload` | checksum + key | checksum/parts → SourceVersion + workflow | 异步 | M3 |
| `GET /spaces/{space_id}/sources` | `source.read` + 密级 | GET | SourceDocument page | 同步 | M3 |
| `GET /sources/{source_id}/versions/{version_id}` | `source.read` + 密级 | GET | SourceVersion metadata | 同步 | M3 |
| `GET /source-versions/{id}/content` | `source.download` + 密级 | GET | 受控下载/流 | 同步 | M3 |
| `GET /source-versions/{id}/preview?anchor=...` | `source.read` + 密级 | GET | sanitized preview + highlight status | 同步 | M3 |
| `POST /source-versions/{id}/parse` | `source.parse` | source+parser+config key | ParseCommand → ParseJob/workflow | 异步 | M3 |
| `POST /source-versions/{id}/invalidate` | `source.invalidate` | command key | reason → new state | 同步 | M3 |
| `POST /spaces/{space_id}/schemas` | `schema.edit` | key | SchemaCreate → definition/version | 同步 | M4 |
| `GET /schemas/{schema_id}/versions/{version}` | `schema.read` | GET | SchemaVersion | 同步 | M4 |
| `POST /schemas/{schema_id}/versions/{version}/validate` | `schema.edit` | content hash | Schema draft → compatibility report | 同步/异步 | M4 |
| `POST /schemas/{schema_id}/versions/{version}/publish` | `schema.publish` + approval | command key + etag | approval → published SchemaVersion | 异步 | M4 |
| `POST /spaces/{space_id}/compile-jobs` | `compile.create` | scope+schema+config key | CompileRequest → CompileJob/workflow | 异步 | M5 |
| `GET /compile-jobs/{job_id}` | `compile.read` | GET | job, steps, errors, cost summary | 同步 | M2/M5 |
| `POST /compile-jobs/{job_id}/pause` | `compile.control` | command key | state transition | 异步 update | M2/M5 |
| `POST /compile-jobs/{job_id}/resume` | `compile.control` | command key | state transition | 异步 update | M2/M5 |
| `POST /compile-jobs/{job_id}/cancel` | `compile.control` | command key | cancellation result | 异步 | M2/M5 |
| `GET /spaces/{space_id}/wiki/pages` | `page.read.draft/release` | GET | Page page + version scope | 同步 | M5 |
| `GET /wiki/pages/{page_id}/versions/{version_id}` | version-scope permission | GET | WikiPageVersion + evidence links | 同步 | M5 |
| `PATCH /wiki/pages/{page_id}/drafts/{version_id}` | `page.edit` | `If-Match` | edits/diff → new page version | 同步 | M5 |
| `GET /wiki/pages/{page_id}/diff` | `page.read` | GET | version diff | 同步 | M5 |
| `GET /spaces/{space_id}/entities` | `knowledge.read` | GET | entities by schema/release | 同步 | M5/M7 |
| `GET /spaces/{space_id}/relations` | `knowledge.read` | GET | relations + evidence status | 同步 | M5/M7 |
| `GET /spaces/{space_id}/claims` | `claim.read` | GET | claims with scope/status | 同步 | M6 |
| `GET /evidence/{evidence_id}` | `evidence.read` + source ACL | GET | Evidence + anchor metadata | 同步 | M6 |
| `GET /evidence/{evidence_id}/content` | `evidence.content.read` + source ACL | GET | permitted excerpt/highlight | 同步 | M6 |
| `GET /spaces/{space_id}/conflicts` | `conflict.read` | GET | conflict queue | 同步 | M6 |
| `POST /conflicts/{id}/resolve` | `conflict.resolve` + separation | command key + etag | resolution/evidence/reason → state | Workflow update | M6 |
| `GET /spaces/{space_id}/reviews` | `review.read` | GET | review queue | 同步 | M6 |
| `POST /reviews/{id}/claim` | `review.act` | command key | assignment result | Workflow update | M6 |
| `POST /reviews/{id}/actions` | `review.act` | action key + etag | accept/edit/reject/request-input | Workflow update | M6 |
| `POST /approvals/{id}/decide` | designated approver | command key + etag | approve/reject + reason | Workflow update | M6/M7 |
| `POST /spaces/{space_id}/evaluations/runs` | `evaluation.run` | suite+target+config key | EvaluationRequest → run/workflow | 异步 | M7 |
| `GET /evaluations/runs/{id}` | `evaluation.read` | GET | metrics/errors/config versions | 同步 | M7 |
| `POST /spaces/{space_id}/release-candidates` | `release.create` | content manifest key | scope/version → candidate | 异步 | M7 |
| `POST /release-candidates/{id}/publish` | `release.publish` + approval | command key + etag | publish command → workflow | 异步 | M7 |
| `GET /spaces/{space_id}/releases` | `release.read` | GET | release history | 同步 | M7 |
| `GET /releases/{release_id}` | `release.read` | GET | immutable manifest/metadata | 同步 | M7 |
| `POST /spaces/{space_id}/release-pointer` | `release.rollback/switch` | command key + etag | target release → pointer | 异步 | M7 |
| `GET /releases/{release_id}/graph/traverse` | `query.release` | GET/query hash | nodes/edges/evidence refs | 同步 | M7 |
| `POST /releases/{release_id}/queries` | `query.release` | client request ID | question/filters → QueryAnswer/Citations | 同步或 async handle | M7 |
| `GET /query-answers/{answer_id}` | answer owner/audit | GET | reproducible answer | 同步 | M7 |
| `GET /domain-packs` | `pack.read` | GET | compatible Pack versions | 同步 | M4 |
| `POST /spaces/{space_id}/domain-pack-installations` | `pack.install` + approval | space+pack version key | InstallRequest → installation/workflow | 异步 | M4 |
| `POST /installations/{id}/rollback` | `pack.rollback` | command key | rollback target → workflow | 异步 | M4 |
| `POST /spaces/{space_id}/connectors` | `connector.manage` | key | config + CredentialRef → Connector | 同步 | M8 |
| `POST /connectors/{id}/sync-runs` | `connector.run` | connector+watermark key | sync request → workflow | 异步 | M8 |
| `GET /connectors/{id}/sync-runs/{run_id}` | `connector.read` | GET | status/errors/watermark | 同步 | M8 |
| `POST /integrations/gridcrew/query` | GridCrew ServiceIdentity; fixed release policy | GridCrew request ID | skill context/question → answer/citations | 同步 | M8 |
| `GET /integrations/gridcrew/releases/{id}/evidence/{eid}` | GridCrew ServiceIdentity + delegated scope | GET | permitted evidence metadata/content | 同步 | M8 |
| `POST /integrations/gridcrew/feedback` | GridCrew ServiceIdentity | task/feedback ID | feedback/case draft → intake workflow | 异步；只入草稿 | M8 |

## M0 契约单一来源与兼容规则

- HTTP 路由/Pydantic 模型导出并提交 OpenAPI 3.1 snapshot；CI 比对实现与 snapshot，更新 snapshot 必须作为公共契约变化评审。
- 跨 HTTP/事件/SDK 的模型以 `packages/contracts` Pydantic 模型为 canonical source，生成并提交 JSON Schema Draft 2020-12；CI 阻断生成物漂移。
- TypeScript/Python SDK 只从已提交 OpenAPI/JSON Schema 生成，不反向修改契约；SDK 尚未在 M0 生成业务方法。
- verified OIDC/service identity 提供 actor/tenant claims；路径/资源 space 与 claims 共同校验。客户端自报 header 不授予租户权限。
- 产生副作用的命令使用 `Idempotency-Key`；可变资源写入使用 `If-Match`；列表使用 opaque cursor；异步命令返回 operation/business ID + Workflow ID。
- 同 major 只允许增加可选字段或新路径。删除、改义、收紧枚举和 Release/Evidence/SourceAnchor 语义变化必须 ADR + 新 major/迁移窗口。
