# Requirements Traceability Matrix

> M3 状态：M2 已正式验收；M3 已于 2026-08-29 正式验收，校准、代码实施、独立审查、本地修复回归、真实 ClamAV-backed Compose E2E、本地 P0 和远程 GitHub Actions run `33253911959` 双架构/SBOM/CVE/Cosign 门禁均已闭环。M2 Kernel Stub 不作为 M3 业务证据；归档 M2 history Replay 和真实 OCR 仍未声称完成。
> `原型` 使用页面名称；`API` 仅引用资源域，详细路径见 API baseline。

## 1. 16 个一级模块

| 需求 ID | 需求来源/原型 | Milestone | 核心对象 | API / Workflow | 测试类型 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|
| NXW-DASH-001 | PRD 8.1 / 总览 | M1,M7 | Space, CompileJob, ReviewTask, Conflict, EvaluationRun, Release | read projections | API/UI/E2E/权限 | VERIFIED（M7 USER ACCEPTED） | M7 API/UI 提供质量、候选、Release 和查询状态；生产规模观测待部署 |
| NXW-SPACE-001 | PRD 8.2 / 知识空间 | M1 | Tenant, KnowledgeSpace, SpaceMember | `/spaces`, memberships | unit/API/E2E/越权 | VERIFIED | 创建、编辑、成员授权/撤销、归档和隔离闭环 |
| NXW-SOURCE-001 | PRD 8.3 / 资料中心 | M3 | SourceDocument, SourceVersion, ParseJob, Segment, Anchor | sources; SourceIngestion v2 | parser/集成/E2E/安全 | VERIFIED；M3 USER ACCEPTED | 真实代码、契约、本地回归、ClamAV-backed Compose E2E 与远程 run `33253911959` 双架构/SBOM/CVE/Cosign 门禁均通过 |
| NXW-COMPILE-001 | PRD 8.5 / 编译中心 | M2,M5 | CompileJob, CompileStep | workflow tasks; KnowledgeCompile | workflow/E2E/故障/幂等 | VERIFIED（M5 本地技术验收） | 固定 Source/Schema/Prompt/Model，v2 Workflow、步骤/成本/审计、稳定输出和新 Job 重试 |
| NXW-WIKI-001 | PRD 8.6 / Wiki | M5,M8 | WikiPage, WikiPageVersion, WikiLinkGraph | wiki pages; wiki-link-graph | unit/API/UI/E2E | VERIFIED（M8 USER ACCEPTED） | diff、人工保护区、追加版本、链接/反链、评论/关注、Evidence 元数据；M8 增加受限的 Obsidian 风格页面双向导航图谱，不等同于 Release Graph |
| NXW-SCHEMA-001 | PRD 8.4 / Schema Studio + ADR-0022 | M4 | SchemaDefinition/Version, EntityType, PropertyDefinition, Hierarchy, RelationType, TypeTerm, ConceptMapping, Template, LintRule | schemas/semantic model | contract/UI/兼容/迁移/确定性 | VERIFIED（M4 本地技术验收） | SchemaVersion 单一语义权威；破坏性变更阻断 |
| NXW-CLAIM-001 | PRD 8.7 / 主张与证据 | M6 | Claim, Evidence, SourceAnchor | claims/evidence | unit/API/E2E/定位 | VERIFIED（M6 USER ACCEPTED） | 支持/反向证据、来源等级 |
| NXW-GRAPH-001 | PRD 8.8 / 关系图谱 | M7 | Entity, Relation, Evidence, Release | graph traverse | unit/API/UI/权限/性能 | VERIFIED（M7 USER ACCEPTED） | 固定 Release、证据/密级过滤、1—5 跳/最短/因果/时间切片；规模性能待部署 |
| NXW-CONFLICT-001 | PRD 8.9 / 冲突中心 | M6 | Conflict, Claim, Relation, Evidence | conflicts; Review | unit/API/E2E/状态机 | VERIFIED（M6 USER ACCEPTED） | 处置保留双方证据并可阻断发布 |
| NXW-REVIEW-001 | PRD 8.10 / 审核中心 | M6 | ReviewTask, ReviewAction, Approval | reviews/approvals; HumanReview | workflow/UI/E2E/职责分离 | VERIFIED（M6 USER ACCEPTED） | 初审、复核、批准、补资料、超时 |
| NXW-QUALITY-001 | PRD 8.11 / 质量中心 | M7 | EvaluationSuite/Run, LintRule | evaluations; QualityEvaluation | eval/回归/UI/门禁 | VERIFIED（M7 USER ACCEPTED） | 固定问题集、逐题错误、检索配置与 100% 发布门禁 |
| NXW-RELEASE-001 | PRD 8.12 / 发布管理 | M7 | ReleaseCandidate, Release, ReleaseItem, Pointer | releases; KnowledgeRelease | workflow/E2E/恢复/不可变 | VERIFIED（M7 USER ACCEPTED） | 两版本独立审批、不可变固化、导出、废止、投影重建和指针回滚已验证 |
| NXW-QUERY-001 | PRD 8.13 / Ask NEXWEAVE | M7 | QuerySession, QueryAnswer, Citation, Release | queries | retrieval/eval/E2E/安全 | VERIFIED（M7 USER ACCEPTED） | 固定 Release、幂等复现、Evidence/Anchor 引用、不确定性与拒答已验证 |
| NXW-PACK-001 | PRD 8.14 / 领域知识包 + ADR-0022 | M4,M9 | DomainPack/Version, Installation, SchemaVersion, CompositionReport | domain packs; PackInstall | manifest/供应链/依赖DAG/组合/兼容/E2E | VERIFIED（M9 LOCAL TECHNICAL） | `equipment-rca-pack@1.0.0` 已签名、真实注册/安装为 ACTIVE，并与公开 Source→Compile 试点贯通；专家验收另行跟踪 |
| NXW-INTEGRATION-001 | PRD 8.15 / 集成中心 | M8 | ConnectorInstance, SyncRun, Obsidian exchange | connectors; ConnectorSync v2 | contract/unit/API/迁移/安全 | VERIFIED（M8 USER ACCEPTED） | 只读 allowlist、CredentialRef、水位、Raw→SourceVersion；GridCrew 按用户指令延期；生产依赖 E2E 仍需在目标环境执行 |
| NXW-ADMIN-001 | PRD 8.16 / 系统管理 | M1 | Tenant, User, ServiceIdentity, ModelProfile, PromptVersion, AuditLog | IAM/admin/audit | API/UI/越权/审计 | VERIFIED | OIDC 兼容接口、本地开发 IdP、RBAC+ABAC、密钥引用、审计和健康 |

## 1.1 M4 语义模型横切需求

| 需求 ID | 需求 | 来源 | Milestone | 对象 / 契约 | 验证 | 状态 |
|---|---|---|---|---|---|---|
| NXW-SEMANTIC-001 | SchemaVersion 作为 R1 唯一有效语义快照，固化 stable keys、类型/属性/层级/关系、术语、映射和 composition checksum | 用户 2026-08-29；ADR-0022 | M4 | SchemaVersion/Semantic Model view | domain/contract/API/UI/version | VERIFIED（单元/契约/真实 API/UI） |
| NXW-SEMANTIC-002 | 多 Pack 依赖解析为精确版本/checksum 并确定性组合；冲突/循环/歧义阻断，安装不自动发布 | 用户 2026-08-29；ADR-0022 | M4,M9,M13 | DomainPackVersion/Installation/CompositionReport | deterministic checksum/Workflow/E2E/security | VERIFIED（M4 runtime；M9/M13 待后续授权） |
| NXW-SEMANTIC-003 | Compile 与 Release 固定 SchemaVersion/composition/Pack 输入，历史可复现且 Schema 合规不替代 Evidence | ADR-0022、0014、0016、0024、0026 | M5,M6,M7 | CompileJob/Release manifest | compile/release/rebuild/E2E | VERIFIED（M7 USER ACCEPTED）；Release 固定清单、Evidence gate 与重建已验证 |
| NXW-SEMANTIC-004 | LLM 仅建议下一 SchemaVersion 的语义变更候选，不自动合并概念或修改发布模型 | ADR-0022、0024 | M5,M6 | SemanticChangeProposal/Review | eval/review/audit/security | VERIFIED（M5 候选写入边界）；人工处置待 M6 |

## 2. MVP 14 项能力

| 需求 ID | MVP 能力 | 来源/原型 | Milestone | 对象 / API | 测试 | 状态 |
|---|---|---|---|---|---|---|
| NXW-SPACE-002 | 创建知识空间 | PRD 16.1-1 / 知识空间 | M1 | Space; `POST /spaces` | API/UI/E2E/权限 | VERIFIED |
| NXW-SOURCE-002 | 上传 PDF、Word、Markdown | PRD 16.1-2 / 资料中心 | M3 | SourceVersion/ParseJob | parser/E2E/恶意文件 | VERIFIED；M3 USER ACCEPTED | 六类 parser、真实扫描/Compose E2E 与远程 run `33253911959` 双架构/SBOM/CVE/Cosign 门禁通过 |
| NXW-SCHEMA-002 | 配置基础实体、属性、层级、关系、术语与映射 | PRD 16.1-3 / Schema Studio + ADR-0022 | M4 | SchemaVersion/semantic definitions | contract/UI/兼容/确定性 | VERIFIED（M4） |
| NXW-COMPILE-002 | LLM 创建/更新 Wiki 草稿 | PRD 16.1-4 / 编译中心、Wiki | M5 | CompileJob/PageVersion | eval/E2E/幂等 | VERIFIED（本地确定性 Provider；外部 LLM adapter 未配置） |
| NXW-CLAIM-002 | 自动提取来源引用 | PRD 16.1-5 / 主张与证据 | M5,M6 | EvidenceCandidate/SourceAnchor | 定位准确率/E2E | VERIFIED（M6 USER ACCEPTED）；正式 Evidence 已受 Review/Evidence gate 约束，未声明准确率阈值 |
| NXW-WIKI-002 | Wiki 编辑和差异展示 | PRD 16.1-6 / Wiki | M5 | PageVersion/diff | UI/API/并发 | VERIFIED（M5 本地技术验收） |
| NXW-REVIEW-002 | 专家审核 | PRD 16.1-7 / 审核中心 | M6 | Review/Approval | Workflow/E2E/职责分离 | VERIFIED（M6 USER ACCEPTED） |
| NXW-CLAIM-003 | Claim/Evidence 查看 | PRD 16.1-8 / 主张与证据 | M6 | claims/evidence | API/UI/权限 | VERIFIED（M6 USER ACCEPTED） |
| NXW-GRAPH-002 | 基础关系图 | PRD 16.1-9 / 关系图谱 | M7 | Relation/GraphPort | API/UI/证据 | VERIFIED（M7 USER ACCEPTED） |
| NXW-CONFLICT-002 | 冲突识别 | PRD 16.1-10 / 冲突中心 | M5,M6 | ConflictCandidate | unit/eval/E2E | VERIFIED（M6 USER ACCEPTED）；ConflictCase 聚类与可审计处置已实现 |
| NXW-QUALITY-002 | Lint 检查 | PRD 16.1-11 / 质量中心 | M4,M5,M7 | LintRule/LintFinding/EvaluationRun | unit/回归/门禁 | VERIFIED（M7 USER ACCEPTED）；Schema/来源/页面批准与问题集门禁已实现，扩展规则持续迭代 |
| NXW-RELEASE-002 | 发布 Markdown/JSON 正式版本 | PRD 16.1-12 / 发布管理 | M7 | Release/Items/export | E2E/不可变/回滚 | VERIFIED（M7 USER ACCEPTED） |
| NXW-QUERY-002 | 基于正式版本可信问答 | PRD 16.1-13 / Ask | M7 | QueryAnswer/Citation | eval/E2E/拒答/权限 | VERIFIED（M7 USER ACCEPTED） |
| NXW-PACK-002 | 安装 RCA 示例领域包并验证公共概念复用 | PRD 16.1-14 / 领域知识包 + ADR-0022 | M4,M9 | PackVersion/Installation/SchemaVersion | manifest/组合/E2E/卸载 | VERIFIED（M9 LOCAL TECHNICAL）；签名 Pack、core 复用、真实 API/Workflow 安装与 4 份公开资料候选编译已验证 |

## 3. 非功能与全局约束

| 需求 ID | 需求 | 来源 | Milestone | 验证 | 状态/备注 |
|---|---|---|---|---|---|
| NXW-NFR-PERF-001 | 普通页面 ≤1s、关键词/属性 ≤2s、混合检索平均 ≤3s、页面打开 ≤2s | PRD 12.1 | M7,M12 | 明确数据集/并发/p95 后性能测试 | BASELINED；“普通页面”口径待冻结 |
| NXW-NFR-PERF-002 | 编译异步，进度更新延迟 ≤3s | PRD 12.1 | M2,M5 | Workflow/UI 延迟测试 | PARTIAL；M2 具备异步步骤投影和真实 UI，未在批准负载/环境下作 ≤3s 性能认证 |
| NXW-NFR-PERF-003 | 百万实体/五百万关系横向扩展设计 | PRD 12.1 | R1 架构、M12 正式验收 | 容量模型/性能环境 | BASELINED；R1 不作规模结论 |
| NXW-NFR-AVL-001 | 核心服务可用性目标 ≥99.9% | PRD 12.2 | M12 | SLI/SLO、故障演练 | BASELINED；R2 正式验收 |
| NXW-NFR-AVL-002 | 编译断点续跑、发布回滚 | PRD 12.2 | M2,M5,M7 | Worker 重启、Replay、回滚 E2E | VERIFIED（M7 USER ACCEPTED）；Release 指针回滚与 Workflow 恢复已验证，专门崩溃窗口/生产演练保留 P2 |
| NXW-NFR-AVL-003 | Raw/Release 备份恢复 | PRD 12.2 | M7,M12 | 备份/恢复/索引重建 | BASELINED |
| NXW-NFR-SEC-001 | HTTPS、OIDC、RBAC+ABAC、密级/空间隔离 | PRD 12.3/13 | M1 | 越权矩阵/传输安全 | PARTIAL；M1 已验证 OIDC 兼容配置、RBAC+ABAC、跨租户/空间/密级隔离；本地 Compose 不作为 HTTPS 终止验收 |
| NXW-NFR-SEC-002 | 模型调用脱敏，高密资料禁止第三方模型 | PRD 12.3 | M1,M5 | 数据流/策略/泄漏测试 | VERIFIED（M5 本地边界）；密级上限与 `HIGHLY_RESTRICTED` 外部 egress 阻断，未配置外部 Provider adapter |
| NXW-NFR-SEC-003 | API 密钥加密/引用，完整审计，SBOM/依赖扫描 | PRD 12.3 | M0,M1 | secret scan/SCA/审计测试 | PARTIAL；M1 业务写入审计/Outbox、配置仅存 Secret 引用并通过 secret/SCA；run 32808198635 的远程 CI、双架构 SBOM/CVE/Cosign 全部通过，生产 Secret Provider 仍待目标环境联调 |
| NXW-NFR-AUD-001 | 知识、模型/Prompt、审核、发布、问答版本可追溯 | PRD 12.4 | M1-M7 | 固定 Release 复现 E2E | VERIFIED（M7 USER ACCEPTED）；Source→Schema→Compile→Review→Release→Citation 固定引用链已闭环 |
| NXW-NFR-COMPAT-001 | Chromium、国产浏览器、离线内网 | PRD 12.5 | R1 基线、M12 正式验收 | 浏览器矩阵/离线安装 | PARTIAL；M1 Web 响应式、键盘语义和生产静态构建通过，国产浏览器矩阵与离线交付认证待后续环境验收 |
| NXW-ARCH-001 | domain/contracts 不依赖框架、数据库、Temporal、厂商 SDK | 总纲 6.2 | M0 起持续 | `tests/architecture/test_dependency_boundaries.py` | VERIFIED（M1 持续，application 亦受边界测试） |
| NXW-ARCH-002 | Workflow 确定性，外部操作仅 Activity | 总纲 6.2 | M2 起持续 | architecture boundary + replay | VERIFIED（M2）；七类 Workflow 模块无 I/O，Activity 独立队列，真实历史 Replay 通过 |
| NXW-ARCH-003 | Search/Vector/Graph 可由 Release 重建 | 总纲 4.2/6.2 | M7 | rebuild E2E | VERIFIED（M7 USER ACCEPTED） |
| NXW-KQ-001 | 发布知识来源可追溯率、Schema 合规率 100% | PRD 18.2/总纲 R1 | M7,M9 | release gate/试点报告 | VERIFIED（M7 USER ACCEPTED GATE）；真实 RCA 试点统计待 M9 |
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
- M3 Source/parse、M4 Schema/Pack、M5 Compile/Wiki、M6 Claim/Evidence/Review、M7 Quality/Release/Graph/Query 与 M8 Connector/Obsidian/Wiki 图谱已正式验收。M9 已正式下发并完成声明式 Equipment RCA Pack 本地技术增量；GridCrew、真实 RCA Release、专家和联合试点不得声称已实现。历史 M2 v1 Workflow 仍只作为 Kernel Stub；
- ADR-0022/0023、Semantic Model Baseline 与 M4 公共契约已在 M4 实现；该完成不授权 M5，也不构成 Compile/Release/RCA 完成；
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
| 时间跳跃 | SDK time-skipping test | integration test | VERIFIED；本地真实执行通过，GitHub Actions run 32808198635 的独立 `temporal-time-skipping` job 通过 |
| 任务中心/API/SDK | 真实列表/详情/步骤/日志/动作/深链接；typed clients | OpenAPI/contract/UI/build/E2E | VERIFIED |
| 数据与迁移 | `0003_m2_temporal_kernel` | 隔离真实 PostgreSQL base/down/up | VERIFIED |

## 8. M3 执行前治理追踪

| M3 要求 | 校准证据 | 当前状态 |
|---|---|---|
| M0—M2 实况对齐 | M3 任务书明确 M2 `source-ingestion.v1` 仅 Kernel Stub，ManagedObject 不是 SourceVersion | IMPLEMENTED；边界测试通过 |
| 失败/部分/retry/reparse/替代 | ADR-0021；OQ-PARSE-001 已关闭 | LOCALLY VERIFIED；并发/终态修复、本地回归与真实 Compose E2E 通过 |
| SourceAnchor | 固定 SourceVersion/checksum/ParseJob，状态使用 VALID/STALE/UNRESOLVED/REVOKED，重定位新建 Anchor | IMPLEMENTED；清单/定位器单测通过 |
| Parser/OCR 与扫描 PDF | ParserPort/OcrPort、真实扫描检测、无真实 OCR 时 `OCR_REQUIRED/PARTIAL`，禁止 Mock 冒充 | IMPLEMENTED；无真实 OCR 声明 |
| Workflow 兼容 | v1 保留 Replay，M3 使用 `nexweave.source-ingestion.v2` 与 ParseJob 稳定 ID | LOCALLY VERIFIED；新建 v1/v2 history replay 通过，已验收归档 M2 history 未取得 |
| 安全/迁移/供应链 | 真实扫描、解析隔离、`0004` additive migration、新依赖治理与真实 E2E 门禁 | VERIFIED；真实 PostgreSQL `0001→0004→0003→0004`、ClamAV clean/EICAR、无凭据沙箱、Compose E2E、本地 ARM64 与远程 run `33253911959` 双架构/SBOM/CVE/Cosign 均通过；可修复 HIGH/CRITICAL=0 |

## 9. M4 语义模型治理校准追踪

| M4 治理要求 | 冻结证据 | 当前状态 |
|---|---|---|
| 单一语义版本权威 | ADR-0022；`SEMANTIC_MODEL_BASELINE.md` | VERIFIED；SchemaVersion/API/DB/UI 单一权威 |
| 对象关系 | EntityType/PropertyDefinition/TypeHierarchyEdge/RelationType/TypeTerm/ConceptMapping/CompositionReport 已进入 Domain/Data baseline | GOVERNANCE FROZEN；无表/API |
| Pack 确定性组合 | 精确依赖 DAG、禁止安装顺序覆盖、composition checksum、安装不自动发布 | VERIFIED；真实签名 Pack/Temporal/PostgreSQL E2E 通过 |
| 版本/兼容/历史 | 破坏性变更阻断；升级/禁用/回滚不改历史 Schema/Pack/Release | VERIFIED；真实升级/禁用/回滚与 append-only 事实通过 |
| M4 执行边界 | 校准后的 `06_NEXWEAVE_M4_Schema Studio与Domain Pack运行时任务书.md` | FORMALLY ACCEPTED（2026-08-30）；用户随后正式下发 M5 |
| M5—M15 影响 | `SEMANTIC_MODEL_IMPACT_MATRIX.md` | 总影响已冻结；各任务书在正式下发前按最近验收实况精确校准 |

## 10. M5 编译与 Wiki 追踪

| M5 要求 | 实现证据 | 当前状态 |
|---|---|---|
| 固定 Compile 输入与稳定身份 | ADR-0024；`knowledge.py`；`compile_jobs`/`compile_job_sources`；真实重复编译 E2E | VERIFIED（本地） |
| Model Gateway 与审计 | `ModelGatewayPort`、本地 no-network Provider、`model_invocations`、预算/密级策略 | VERIFIED（本地 Provider）；外部 adapter 未配置 |
| 候选知识与 Evidence Native | Entity/Relation/Claim/Evidence/Conflict/Lint 候选表、SourceAnchor FK、M5 E2E | VERIFIED（候选边界）；正式审核待 M6 |
| Wiki 保护区与版本 | append-only PageVersion trigger、diff/edit API、重编译保护区 E2E、Wiki UI | VERIFIED（本地） |
| Workflow 兼容 | v1 Stub 保留、v2 真实 Activity、Workflow sandbox/注册测试 | VERIFIED（新历史与定义）；归档生产历史未单独导入 |
| M5 执行边界 | M5 任务书、ADR-0024、M5 执行报告 | FORMALLY ACCEPTED；后续 M6、M7 均已正式验收 |

## 11. M6 正式知识与审核追踪

| M6 要求 | 实现证据 | 当前状态 |
|---|---|---|
| Claim/Evidence 正式化与 Anchor gate | ADR-0025、`0007_m6`、HumanReview v2、M6 E2E | VERIFIED（M6 USER ACCEPTED） |
| 冲突聚类与追加决策 | ConflictCase/Item/Decision、阻断发布语义 | VERIFIED（M6 USER ACCEPTED） |
| 高风险分阶段职责分离 | ReviewPolicy/Case/Task/Action，三人真实链路 | VERIFIED（M6 USER ACCEPTED） |

## 12. M7 质量、发布、图谱与问答追踪

| M7 要求 | 实现证据 | 当前状态 |
|---|---|---|
| 版本化问题集、逐题结果与门禁 | ADR-0026、EvaluationSuite/Run/Result、QualityEvaluation v2 | VERIFIED（LOCAL TECHNICAL ACCEPTANCE） |
| 不可变发布与独立审批 | ReleaseCandidate/Item、Release/Item、KnowledgeRelease v2、数据库 immutable guards | VERIFIED（LOCAL TECHNICAL ACCEPTANCE） |
| 回滚、废止、导出与历史 | 强 ETag Pointer/History、Deprecation、JSON/Markdown export | VERIFIED（LOCAL TECHNICAL ACCEPTANCE） |
| 混合检索与可重建投影 | Search/Vector/Graph ports、PostgreSQL FTS/pgvector、RRF、projection rebuild | VERIFIED（LOCAL TECHNICAL ACCEPTANCE） |
| 可信问答 | 单一 Release、密级/Evidence/VALID Anchor 过滤、幂等引用复现与无证据拒答 | VERIFIED（LOCAL TECHNICAL ACCEPTANCE） |
| 真实 E2E | 隔离数据库 + 专用 Temporal 队列，两次 Release、查询复现、拒答、重建、指针回滚 | VERIFIED；共享 M6 数据与指针未修改 |
| M7 执行边界 | M7 任务书、ADR-0026、M7 执行报告 | FORMALLY ACCEPTED（2026-08-31）；后续 M8 已单独下发并验收 |

## 13. M8 集成、Obsidian 与 Wiki 图谱追踪

| M8 要求 | 实现证据 | 当前状态 |
|---|---|---|
| 只读 Connector 与出站控制 | ADR-0027、`0009_m8_connector_obsidian`、ConnectorInstance/SyncRun、显式 allowlist 与 CredentialRef | VERIFIED（M8 USER ACCEPTED） |
| Raw 至 SourceVersion 的可追溯同步 | ConnectorSync v2、M3 Source/Parse 路径、审计执行事实 | VERIFIED（M8 USER ACCEPTED） |
| Obsidian 草稿交换与冲突保护 | 稳定 page ID、base/checksum frontmatter、三方差异、冲突记录 | VERIFIED（M8 USER ACCEPTED） |
| Wiki 双向链接导航图谱 | ADR-0028、受限 graph API、页面链接/反向引用、Web 2D 交互与 18 项测试 | VERIFIED（M8 USER ACCEPTED） |
| GridCrew 首期集成 | 用户明确延期；无对端端点、Webhook、SDK 或 Skill 绑定实现 | DEFERRED（不属于 M8 验收范围） |

## 14. M9 Equipment RCA Pack 与联合试点追踪

| M9 要求 | 实现证据 | 当前状态 |
|---|---|---|
| 声明式 Equipment RCA Pack V1.0 | ADR-0029；`domain-packs/equipment-rca/`；Ed25519/checksum 验证 | VERIFIED（LOCAL TECHNICAL） |
| Schema、术语、模板、Prompt、Lint 与标准问题集 | `semantic.json`、`authoring.json`、`evaluation.json` | VERIFIED（LOCAL TECHNICAL）；专家内容确认待真实试点 |
| 跨 Pack 公共概念复用 | core + equipment-rca + maintenance 确定性组合；公共 Equipment 单一 | VERIFIED（PURE DOMAIN） |
| 平台/领域解耦与可卸载 | 运行时代码无 RCA stable key/KKS；不含 RCA Pack 时 core + maintenance 仍组合 | VERIFIED（LOCAL TECHNICAL） |
| Source→Compile→Review→Evaluate→Release | 9 份资料已准入；4 份代表性报告完成 Raw/文本派生 Source、368 ClaimCandidate、377 EvidenceCandidate 和审计 | IN PROGRESS（Source→Compile 已真实完成；P0 专家 Review/阈值，故未执行 Evaluate/Release/Query） |
| 专家接受率、引用准确率、覆盖率、修改比例 | 空白测量模板，保留分子/分母和失败样本要求 | BLOCKED（P0：专家/阈值缺失） |
| GridCrew 固定 Release 联合 Demo | ADR-0030；用户明确 GridCrew 暂不开发、联合试点延期 | DEFERRED（不属于 M9/R1 验收；不得声称完成） |

## 15. M9-FE 前端设计系统与高保真原型对齐追踪

| 需求 ID | M9-FE 要求 | 实现证据 | 验证 | 当前状态 |
|---|---|---|---|---|
| NXW-FE-001 | 冻结唯一设计系统、页面映射、组件契约、依赖与迁移策略 | `docs/design/NEXWEAVE_FRONTEND_DESIGN_SYSTEM_BASELINE.md`；`apps/web/src/styles/tokens.css`；`apps/web/src/design-system/` | 文档审查、token 扫描、frontend gates | VERIFIED（M9-FE LOCAL TECHNICAL） |
| NXW-FE-002 | 登录与全部已实现路由统一迁移至 App Shell，不伪造 API 或状态 | `LoginPage.tsx`、`OverviewPage.tsx`、`SpacesPage.tsx`、`AdminPage.tsx`、`App.tsx`、17 个受保护路由和真实 `/tasks` 入口 | 22 项 Vitest、真实本地 API/Compose 浏览器遍历 | VERIFIED（M9-FE LOCAL TECHNICAL） |
| NXW-FE-003 | 高保真深色语言、三档响应式、键盘焦点、减少动画和长内容稳定 | 分层 CSS；`docs/development/evidence/m9-fe/{baseline,final}/` | 1440×900、1024×768、390×844；无页面级横向溢出；焦点 2px 可见 | VERIFIED（M9-FE LOCAL TECHNICAL） |
| NXW-FE-004 | 保留 API、权限、错误、深链接、刷新与浏览器历史语义 | 既有 API clients/业务页面保持；`/tasks/:id` 与 `/compile/:id` 兼容；真实 safe-error 未隐藏 | format/lint/typecheck/test/build；浏览器 back/forward；干净控制台 | VERIFIED（M9-FE LOCAL TECHNICAL） |
| NXW-FE-005 | 独立审查、修复、报告并停止，不进入 M10 | M9-FE 独立审查记录与执行验收报告 | P0/P1 复核、范围/依赖/迁移检查 | VERIFIED（M9-FE LOCAL TECHNICAL；不构成 M9 用户验收） |
| NXW-FE-006 | 系统级 UX/UI 整改：错误、研发信息隔离、业务导航、任务型页面、桌面大屏与逐项验收 | `docs/design/FRONTEND_UI_AUDIT.md`；`docs/design/FRONTEND_DESIGN_SYSTEM.md`；`docs/development/reports/FRONTEND_REFACTOR_REPORT.md` | 22 项 Web 测试；format/type/lint/build；1366/1440/1920/2560 浏览器检查；8080 容器 | PASS（P0/Acceptance）；PARTIAL（报告列明的页面深化项） |

## 16. M9.5 可运行 Living Knowledge 首片（2026-09-08）

| ID | 要求 | 实现与验证 | 状态 |
|---|---|---|---|
| NXW-LK-001 | 不以 M9 验收阻塞 M9.5；保留 R1 边界 | 11B、ADR-0032、执行报告 | VERIFIED / TECHNICAL SLICE |
| NXW-LK-002 | Source → Binding → Schema Context | 受控 CSV、时序契约、单元/负向/真实数据库验证 | VERIFIED / CSV ONLY |
| NXW-LK-003 | Provider 可替换、真实 Chronos-2 | 独立 Gateway、Chronos2/Persistence、升级后真实 E2E、依赖审计 | VERIFIED / LOCAL CPU |
| NXW-LK-004 | Forecast 与 Evidence/Release 分离 | 不可变三表、对象哈希、权限拒绝、Potential Event 不给故障概率 | VERIFIED / ARTIFACT OWNED VALUES |
| NXW-LK-005 | Wiki/Graph/Ask 活化 | 五个既有路由的显式运行态预览、真实曲线与条件场景、Wiki 回链 | PARTIAL：图投影/自由问答/知识检索回接待深化 |
| NXW-LK-006 | P-101 Vertical Slice 与长期演进 | 合成数据真实软件/模型链路；Pack 开发 overlay | PARTIAL：工业 Benchmark、签名 Pack、已发布 RCA 引用待补 |

## 17. 阶段 A 稳定基础（2026-09-09）

依据用户 2026-09-08 明确下发、11C 任务书、ADR-0033。仅软件技术验收，不关闭 M9 专家/阈值 P0。

| ID | 要求 | 实现与证据 | 状态 |
|---|---|---|---|
| NXW-LK-A-001 | 统一启动、代码版本、可选预测服务健康 | local_runtime/run_m95_worker、Makefile、runtime 契约；重复启动同一 PID、make dev-up、运行手册 | VERIFIED / LOCAL |
| NXW-LK-A-002 | 受理不丢失、投递恢复、崩溃重试、唯一制品 | 0011_m95a、ForecastRecovery、v2 Workflow；Temporal 中断补发、活动 heartbeat retry attempt=2、数据库/对象哈希核对 | VERIFIED / REAL E2E |
| NXW-LK-A-003 | 可取消、保留冻结输入的新运行、当前权限 | cancel/retry API、终态行锁、前端幂等；运行/排队取消无制品、冻结 Context 相等、失败重跑、3 项越权拒绝 | VERIFIED / REAL E2E |
| NXW-LK-A-004 | 请求追踪隔离 | ASGI 外层隔离；继承 span/并发单元测试、实际上传后长连接与并发请求 | VERIFIED / HTTP |
| NXW-LK-A-005 | R1 完整软件链路与迁移保全 | 独立合成空间 Source→Compile→Review→Evidence/Claim→Release→Query/rollback；0011 升降再升与旧哨兵数据保留 | VERIFIED / SYNTHETIC SOFTWARE ONLY |

统一证据索引：`docs/development/reports/NEXWEAVE_阶段A_稳定基础执行报告.md` 和 `阶段A_运行证据.json`。阶段 B、M10、工业模型效果、签名时序 Pack、发布知识引用合成仍未下发或未完成。

## 18. 阶段 B 自主运行（2026-09-09）

用户已明确下发 B，覆盖上一节历史停止说明；依据 11D / ADR-0034，本地技术完成，不等同用户正式验收。

| ID | 要求 | 实现与证据 | 状态 |
|---|---|---|---|
| NXW-LK-B-001 | 已有受控资料、已发布 Schema 与最小对象选择 | CSV preview、binding-entities、绑定向导；真实资源接口和有界预览 | VERIFIED / LOCAL API |
| NXW-LK-B-002 | 映射/单位/时间/质量预检，保存重验与幂等 | BindingService、共享 CSV 校验；错误映射 4 次拒绝、预检不持久化、重放/冲突 | VERIFIED / REAL API + UNIT |
| NXW-LK-B-003 | 无脚本绑定交互、失败重试和显式未来输入 | BindingWizard、LivingKnowledge；组件测试、类型/构建、8080 部署资产 | VERIFIED / COMPONENT；未新增完整浏览器点击验收 |
| NXW-LK-B-004 | 同历史窗口条件场景比较 | ForecastComparison、livingComparison；两个真实 Chronos-2 制品及兼容性测试 | VERIFIED / SYNTHETIC MODEL E2E |
| NXW-LK-B-005 | 权限、源失效和公开契约边界收口 | 4 项越权拒绝、失效源 3 项拒绝、Source 列表/详情/归档回归；无新迁移 | VERIFIED / REAL API + UNIT |

证据：`docs/development/reports/NEXWEAVE_阶段B_自主运行执行报告.md` 与 `阶段B_运行证据.json`。工业 Benchmark、M9 专家批准、签名时序 Pack、RCA 引用合成及旧 Graph 隔离疑点保持开放。停止在 B，不进入 C/M10。

## 19. 阶段 C 固定发布知识回接（2026-09-09）

依据用户后续下发、11E / ADR-0035，替代 B 的历史停止边界；仅本地技术验证。

| ID | 要求 | 实现与验证 | 状态 |
|---|---|---|---|
| NXW-LK-C-001 | 固定 Release 的独立知识回接，不改旧预测 | 新 knowledge-context 契约/服务，复用 Query/Gateway；双 Release 分别引用、旧制品全文/哈希不变 | VERIFIED / REAL API |
| NXW-LK-C-002 | 只展示当前可见有效的发布快照和引用 | 同空间/权限、Claim/Evidence 发布成员、密级、Anchor/源有效性门禁；跨空间 404、非成员 403、失效后无引用 | VERIFIED / UNIT + REAL API |
| NXW-LK-C-003 | 现有页面内解释与原文追溯 | ForecastKnowledge 组件、发布选择/输入清除/异步隔离/失败重试；3 个新增组件测试、真实原文定位 API、8080 部署 | VERIFIED / COMPONENT + API；无完整浏览器验收 |
| NXW-LK-C-004 | 合成真实闭环、审计及长期边界 | 新资料→审核→发布→既有 Chronos 制品回接，正常参考保留，测试指针恢复；157 Python、31 Web，无新迁移/依赖 | VERIFIED / SYNTHETIC SOFTWARE |

证据：`docs/development/reports/NEXWEAVE_阶段C_知识回接执行报告.md` 与 `阶段C_运行证据.json`。已完成软件引用回接；工业适用性、真实 RCA 专家与旧 Graph/Query 全面复核仍开放。停止在 C，不进入 M10。

## 20. 阶段 D 验收与可信边界收口（2026-09-10）

用户下发 11F / ADR-0036，覆盖 C 停止说明；仅本地技术验证。

| ID | 要求 | 实现与验证 | 状态 |
|---|---|---|---|
| NXW-LK-D-001 | 新 Query 仅使用当前有效引用支持的冻结主张 | release_repository；真实 HTTP、支持文本单测、多来源密级 PostgreSQL 测试 | VERIFIED / LOCAL |
| NXW-LK-D-002 | 历史读取重新鉴权/过滤，重放核对全部请求 | 读时响应投影，无存储改写；历史失效答案 REFUSED、5 类重放差异 409 | VERIFIED / REAL HTTP |
| NXW-LK-D-003 | 固定发布 Graph 成员/来源/证据与预算门禁 | release_graph；真实 API、6 项 PostgreSQL 验证、环/深度/最短路/截断单测、页面旧响应清理 | VERIFIED / LOCAL |
| NXW-LK-D-004 | B/C 关键浏览器路径验证并修复故障 | 1440 行 CSV 预检、改单位禁存/拒绝、已有同窗口分位比较、知识回接、原文 VALID 定位、Graph 切换与拒绝 | VERIFIED / BROWSER |
| NXW-LK-D-005 | 保持 R1 与 Forecast 权威，兼容现有运行 | 162 Python、33 Web；哈希核验、无迁移/依赖、worker d1 在线；Secret scan | VERIFIED / SYNTHETIC SOFTWARE |

证据：`docs/development/reports/NEXWEAVE_阶段D_验收与可信边界执行报告.md` 与 `阶段D_运行证据.json`。覆盖列明的浏览器路径，不声明全站或全安全组合验收。工业 Benchmark、M9 专家批准、签名时序 Pack、现场 Connector 与生产高可用仍开放。停止在 D，不进入 M10。
