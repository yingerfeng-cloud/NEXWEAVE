# Requirements Traceability Matrix

> M2 状态：M1 平台基础已验收；M2 通用 Temporal 可靠内核、任务投影和任务中心可标记 `VERIFIED`/`PARTIAL`。七类 Kernel Stub 不使 M3+ 同名知识业务变为已实现。
> `原型` 使用页面名称；`API` 仅引用资源域，详细路径见 API baseline。

## 1. 16 个一级模块

| 需求 ID | 需求来源/原型 | Milestone | 核心对象 | API / Workflow | 测试类型 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|
| NXW-DASH-001 | PRD 8.1 / 总览 | M1,M7 | Space, CompileJob, ReviewTask, Conflict, EvaluationRun, Release | read projections | API/UI/E2E/权限 | PARTIAL | M1 已实现真实 Space/Audit 概览；知识流水线指标待 M7 |
| NXW-SPACE-001 | PRD 8.2 / 知识空间 | M1 | Tenant, KnowledgeSpace, SpaceMember | `/spaces`, memberships | unit/API/E2E/越权 | VERIFIED | 创建、编辑、成员授权/撤销、归档和隔离闭环 |
| NXW-SOURCE-001 | PRD 8.3 / 资料中心 | M3 | SourceDocument, SourceVersion, ParseJob, Segment, Anchor | sources; SourceIngestion | parser/集成/E2E/安全 | BASELINED | Raw、checksum、版本、预览、失败重试 |
| NXW-COMPILE-001 | PRD 8.5 / 编译中心 | M2,M5 | CompileJob, CompileStep | workflow tasks; KnowledgeCompile | workflow/E2E/故障/幂等 | PARTIAL | M2 已验证通用步骤图、查询/控制/恢复；真实 Source/Schema/Prompt/Model 锁定与 CompileJob 输出待 M5 |
| NXW-WIKI-001 | PRD 8.6 / Wiki | M5 | WikiPage, WikiPageVersion, Entity | wiki pages | unit/API/UI/E2E | BASELINED | diff、人工保护区、不可覆盖版本 |
| NXW-SCHEMA-001 | PRD 8.4 / Schema Studio | M4 | SchemaDefinition/Version, EntityType, RelationType, Template, LintRule | schemas | contract/UI/兼容/迁移 | BASELINED | 破坏性变更阻断 |
| NXW-CLAIM-001 | PRD 8.7 / 主张与证据 | M6 | Claim, Evidence, SourceAnchor | claims/evidence | unit/API/E2E/定位 | BASELINED | 支持/反向证据、来源等级 |
| NXW-GRAPH-001 | PRD 8.8 / 关系图谱 | M7 | Entity, Relation, Evidence, Release | graph traverse | unit/API/UI/权限/性能 | BASELINED | 图是投影，关系有证据 |
| NXW-CONFLICT-001 | PRD 8.9 / 冲突中心 | M6 | Conflict, Claim, Relation, Evidence | conflicts; Review | unit/API/E2E/状态机 | BASELINED | 处置保留双方证据并可阻断发布 |
| NXW-REVIEW-001 | PRD 8.10 / 审核中心 | M6 | ReviewTask, ReviewAction, Approval | reviews/approvals; HumanReview | workflow/UI/E2E/职责分离 | BASELINED | 初审、复核、批准、补资料、超时 |
| NXW-QUALITY-001 | PRD 8.11 / 质量中心 | M7 | EvaluationSuite/Run, LintRule | evaluations; QualityEvaluation | eval/回归/UI/门禁 | BASELINED | 问题级错误与发布门禁 |
| NXW-RELEASE-001 | PRD 8.12 / 发布管理 | M7 | ReleaseCandidate, Release, ReleaseItem, Pointer | releases; KnowledgeRelease | workflow/E2E/恢复/不可变 | BASELINED | 发布、回滚、废止和历史查询 |
| NXW-QUERY-001 | PRD 8.13 / Ask NEXWEAVE | M7 | QuerySession, QueryAnswer, Citation, Release | queries | retrieval/eval/E2E/安全 | BASELINED | 固定 Release、引用、不确定性、拒答 |
| NXW-PACK-001 | PRD 8.14 / 领域知识包 | M4,M9 | DomainPack/Version, Installation, SchemaVersion | domain packs; PackInstall | manifest/供应链/兼容/E2E | BASELINED | 声明式，无任意代码 |
| NXW-INTEGRATION-001 | PRD 8.15 / 集成中心 | M8 | Connector, SyncRun, ServiceIdentity | connectors/GridCrew | contract/集成/E2E/安全 | BASELINED | Source/权限/审计/水位/幂等 |
| NXW-ADMIN-001 | PRD 8.16 / 系统管理 | M1 | Tenant, User, ServiceIdentity, ModelProfile, PromptVersion, AuditLog | IAM/admin/audit | API/UI/越权/审计 | VERIFIED | OIDC 兼容接口、本地开发 IdP、RBAC+ABAC、密钥引用、审计和健康 |

## 2. MVP 14 项能力

| 需求 ID | MVP 能力 | 来源/原型 | Milestone | 对象 / API | 测试 | 状态 |
|---|---|---|---|---|---|---|
| NXW-SPACE-002 | 创建知识空间 | PRD 16.1-1 / 知识空间 | M1 | Space; `POST /spaces` | API/UI/E2E/权限 | VERIFIED |
| NXW-SOURCE-002 | 上传 PDF、Word、Markdown | PRD 16.1-2 / 资料中心 | M3 | SourceVersion/ParseJob | parser/E2E/恶意文件 | BASELINED |
| NXW-SCHEMA-002 | 配置基础实体与关系 Schema | PRD 16.1-3 / Schema Studio | M4 | SchemaVersion/Types | contract/UI/兼容 | BASELINED |
| NXW-COMPILE-002 | LLM 创建/更新 Wiki 草稿 | PRD 16.1-4 / 编译中心、Wiki | M5 | CompileJob/PageVersion | eval/E2E/幂等 | BASELINED |
| NXW-CLAIM-002 | 自动提取来源引用 | PRD 16.1-5 / 主张与证据 | M5,M6 | Evidence/SourceAnchor | 定位准确率/E2E | BASELINED |
| NXW-WIKI-002 | Wiki 编辑和差异展示 | PRD 16.1-6 / Wiki | M5 | PageVersion/diff | UI/API/并发 | BASELINED |
| NXW-REVIEW-002 | 专家审核 | PRD 16.1-7 / 审核中心 | M6 | Review/Approval | Workflow/E2E/职责分离 | BASELINED |
| NXW-CLAIM-003 | Claim/Evidence 查看 | PRD 16.1-8 / 主张与证据 | M6 | claims/evidence | API/UI/权限 | BASELINED |
| NXW-GRAPH-002 | 基础关系图 | PRD 16.1-9 / 关系图谱 | M7 | Relation/GraphPort | API/UI/证据 | BASELINED |
| NXW-CONFLICT-002 | 冲突识别 | PRD 16.1-10 / 冲突中心 | M5,M6 | Conflict | unit/eval/E2E | BASELINED |
| NXW-QUALITY-002 | Lint 检查 | PRD 16.1-11 / 质量中心 | M4,M7 | LintRule/EvaluationRun | unit/回归/门禁 | BASELINED |
| NXW-RELEASE-002 | 发布 Markdown/JSON 正式版本 | PRD 16.1-12 / 发布管理 | M7 | Release/Items/export | E2E/不可变/回滚 | BASELINED |
| NXW-QUERY-002 | 基于正式版本可信问答 | PRD 16.1-13 / Ask | M7 | QueryAnswer/Citation | eval/E2E/拒答/权限 | BASELINED |
| NXW-PACK-002 | 安装 RCA 示例领域包 | PRD 16.1-14 / 领域知识包 | M4,M9 | PackVersion/Installation | manifest/E2E/卸载 | BASELINED |

## 3. 非功能与全局约束

| 需求 ID | 需求 | 来源 | Milestone | 验证 | 状态/备注 |
|---|---|---|---|---|---|
| NXW-NFR-PERF-001 | 普通页面 ≤1s、关键词/属性 ≤2s、混合检索平均 ≤3s、页面打开 ≤2s | PRD 12.1 | M7,M12 | 明确数据集/并发/p95 后性能测试 | BASELINED；“普通页面”口径待冻结 |
| NXW-NFR-PERF-002 | 编译异步，进度更新延迟 ≤3s | PRD 12.1 | M2,M5 | Workflow/UI 延迟测试 | PARTIAL；M2 具备异步步骤投影和真实 UI，未在批准负载/环境下作 ≤3s 性能认证 |
| NXW-NFR-PERF-003 | 百万实体/五百万关系横向扩展设计 | PRD 12.1 | R1 架构、M12 正式验收 | 容量模型/性能环境 | BASELINED；R1 不作规模结论 |
| NXW-NFR-AVL-001 | 核心服务可用性目标 ≥99.9% | PRD 12.2 | M12 | SLI/SLO、故障演练 | BASELINED；R2 正式验收 |
| NXW-NFR-AVL-002 | 编译断点续跑、发布回滚 | PRD 12.2 | M2,M7 | Worker 重启、Replay、回滚 E2E | PARTIAL；M2 Worker 重启继续、历史 Replay、任务对账通过；真实 Compile 断点与 Release 指针回滚待 M5/M7 |
| NXW-NFR-AVL-003 | Raw/Release 备份恢复 | PRD 12.2 | M7,M12 | 备份/恢复/索引重建 | BASELINED |
| NXW-NFR-SEC-001 | HTTPS、OIDC、RBAC+ABAC、密级/空间隔离 | PRD 12.3/13 | M1 | 越权矩阵/传输安全 | PARTIAL；M1 已验证 OIDC 兼容配置、RBAC+ABAC、跨租户/空间/密级隔离；本地 Compose 不作为 HTTPS 终止验收 |
| NXW-NFR-SEC-002 | 模型调用脱敏，高密资料禁止第三方模型 | PRD 12.3 | M1,M5 | 数据流/策略/泄漏测试 | PARTIAL；M1 模型配置禁止外部 Profile 接收 `HIGHLY_RESTRICTED`，真实模型数据流待 M5 |
| NXW-NFR-SEC-003 | API 密钥加密/引用，完整审计，SBOM/依赖扫描 | PRD 12.3 | M0,M1 | secret scan/SCA/审计测试 | PARTIAL；M1 业务写入审计/Outbox、配置仅存 Secret 引用并通过本地 secret/SCA；生产 Secret Provider 与本次提交的外部 CI 重跑待部署流程 |
| NXW-NFR-AUD-001 | 知识、模型/Prompt、审核、发布、问答版本可追溯 | PRD 12.4 | M1-M7 | 固定 Release 复现 E2E | PARTIAL；M1 ModelProfile/PromptVersion/ConnectorDefinition 版本、审计和事件可追溯，知识链路待 M3—M7 |
| NXW-NFR-COMPAT-001 | Chromium、国产浏览器、离线内网 | PRD 12.5 | R1 基线、M12 正式验收 | 浏览器矩阵/离线安装 | PARTIAL；M1 Web 响应式、键盘语义和生产静态构建通过，国产浏览器矩阵与离线交付认证待后续环境验收 |
| NXW-ARCH-001 | domain/contracts 不依赖框架、数据库、Temporal、厂商 SDK | 总纲 6.2 | M0 起持续 | `tests/architecture/test_dependency_boundaries.py` | VERIFIED（M1 持续，application 亦受边界测试） |
| NXW-ARCH-002 | Workflow 确定性，外部操作仅 Activity | 总纲 6.2 | M2 起持续 | architecture boundary + replay | VERIFIED（M2）；七类 Workflow 模块无 I/O，Activity 独立队列，真实历史 Replay 通过 |
| NXW-ARCH-003 | Search/Vector/Graph 可由 Release 重建 | 总纲 4.2/6.2 | M7 | rebuild E2E | BASELINED |
| NXW-KQ-001 | 发布知识来源可追溯率、Schema 合规率 100% | PRD 18.2/总纲 R1 | M7,M9 | release gate/试点报告 | BASELINED |
| NXW-KQ-002 | 引用准确率、问题覆盖率、专家接受率达到约定阈值 | PRD 18.2/M9 | M9 | 盲审样本/评测报告 | BASELINED；阈值 P0 未定 |

## 4. M0 工程骨架追踪

| M0 要求 | 实现/证据 | 自动验证 | 状态 |
|---|---|---|---|
| C4/ADR/终局技术栈冻结 | `ARCHITECTURE_BASELINE.md`、C4 baseline、ADR-0001—0018 | 文档/状态检查 | IMPLEMENTED |
| ID/状态/权限/错误/SourceAnchor/Release | pure domain、contract schemas、state/permission/error baseline | unit + JSON Schema + snapshot | VERIFIED |
| API/事件/幂等/投影契约 | API/event baselines、ADR-0015/0016、OpenAPI/event schema | contract tests | VERIFIED |
| Python/TypeScript Monorepo | `apps/`, `packages/`, `workers/`, root commands | lint/typecheck/unit/build | VERIFIED |
| 最小 API/Web/Worker | health/version/diagnostics、status Web、Temporal health Workflow | unit/UI + Temporal test server + Compose E2E | VERIFIED；真实 Web/API/依赖探测与 Compose Worker Workflow 全链路通过 |
| 基础迁移 | `0001_m0_platform_foundation` | real PostgreSQL upgrade/down/up | VERIFIED；真实 PostgreSQL downgrade/upgrade/downgrade/upgrade 通过并回到唯一 head |
| 可复现本地环境 | `compose.yaml`、Dockerfiles、runbook；RustFS 选型见 ADR-0017 | `make dev-up`, `make verify` | VERIFIED；官方 Docker Hub/Quay 镜像已拉齐，七个 M0 服务一键启动，完整真实 E2E 通过 |
| CI/安全/依赖治理 | CI workflow、secret scan、exact locks、dependency baseline | local gates/audits + GitHub CI | VERIFIED（M0）；run 32702688049 六个 job 全绿，四类镜像双架构 SBOM/CVE/Cosign 证据已上传 |

## 5. M1 实现追踪

| M1 要求 | 实现/证据 | 自动验证 | 状态 |
|---|---|---|---|
| 身份、OIDC 与服务身份 | `IdentityProviderPort`、local/OIDC adapter、audience 与最小角色策略 | unit/contract/E2E | VERIFIED |
| RBAC+ABAC 与隔离 | tenant/space/成员/状态/密级默认拒绝；拒绝审计 | 权限单测 + 跨租户/跨空间真实 E2E | VERIFIED |
| 空间与成员闭环 | Space CRUD/归档、成员授权/撤销、ETag、幂等、Web UI | API/UI/真实 E2E | VERIFIED |
| 治理配置 | User、ServiceIdentity、ModelProfile、PromptVersion、ConnectorDefinition、AuditLog | contract/API/UI/E2E | VERIFIED（仅配置事实，不执行模型或 Connector） |
| 对象存储基础 | `ObjectStoragePort`、RustFS adapter、受控上传、checksum、扫描状态、重新授权下载 | 真实 RustFS E2E | VERIFIED（ManagedObject 不是 SourceVersion） |
| 审计、Outbox、可观测性 | 业务事务内 append-only Audit/Outbox；W3C trace；OTel Web/API/DB/S3 | contract/DB/E2E | VERIFIED |
| 数据与迁移 | `0002_m1_platform_services`，升级/回滚/再升级 | 真实 PostgreSQL migration check | VERIFIED |
| 契约与 SDK | OpenAPI、JSON Schema、事件、Python/TypeScript SDK | snapshot/contract/typecheck | VERIFIED |

## 6. 覆盖结论

- PRD 16 个一级模块：16/16 已映射；
- MVP 必须完成能力：14/14 已独立映射；
- PRD 性能、可用性、安全、审计和兼容性：已建立基线行；
- M1 已真实实现 KnowledgeSpace 与系统管理基础；M2 已实现通用 WorkflowTask/Step/Event、Temporal 执行控制与任务中心；
- Source、Schema、真实 Compile、Wiki、Claim、Graph、Conflict、Review、Quality、Release、Query、Pack 和 Integration 业务仍未实现；七类 Workflow 只产生 `business_features_implemented=false` 的 Kernel Stub 结果；
- M2 已把任务端点映射到 OpenAPI/Schema/Event/SDK/测试；后续业务资源仍随对应 Milestone 契约先行落地，禁止提前伪造；
- 试点质量阈值仍由产品/RCA 专家决定，M0 不以未经批准的数字关闭 NXW-KQ-002。

## 7. M2 实现追踪

| M2 要求 | 实现/证据 | 自动验证 | 状态 |
|---|---|---|---|
| Namespace、队列与 Worker | `nexweave-dev`、分离 Workflow/Activity queue、`worker-kernel` | Compose health + queue describe | VERIFIED |
| 七类 Workflow 与稳定标识 | 版本化名称、稳定 business key/Workflow ID、Run ID 映射、三步 Kernel Stub | domain/contract + 七类真实 E2E | VERIFIED（内核边界） |
| 控制、人工等待与幂等 | Update/Signal、pause/resume/cancel/review/retry、ETag、命令 key | unit/contract + duplicate/approval E2E | VERIFIED |
| Activity 可靠性 | timeout、指数重试、不可重试错误、heartbeat、取消与补偿 | fault injection + cancellation compensation | VERIFIED |
| 投影与对账 | Task/Step/append-only Event、revision/sync、Temporal reconcile | DB trigger + corruption/repair E2E | VERIFIED |
| Worker 恢复与确定性 | Worker stop/start、继续执行、历史 Replayer | real Temporal fault/replay drill | VERIFIED |
| 时间跳跃 | SDK time-skipping test | integration test | CONDITIONAL；外部 test-server 初始化未完成，未取得通过结果 |
| 任务中心/API/SDK | 真实列表/详情/步骤/日志/动作/深链接；typed clients | OpenAPI/contract/UI/build/E2E | VERIFIED |
| 数据与迁移 | `0003_m2_temporal_kernel` | 隔离真实 PostgreSQL base/down/up | VERIFIED |
