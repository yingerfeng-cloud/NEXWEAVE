# NEXWEAVE Open Questions

> 状态值：`OPEN`、`PROPOSED`、`DECIDED`、`DEFERRED`。  
> M0—M8 已正式验收，M9 已于 2026-09-01 正式下发。任何仍未决事项不得被编码静默固化；M9 未验收且未明确下发 M10 前不得进入 M10。

## 已明确

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-REL-001 | DECIDED | 当前 Release 统一采用 R1=M0—M9、R2=M10—M12、R3=M13—M15 | 用户 2026-08-23 明确“统一”；完整开发总纲 |
| OQ-PROD-001 | DECIDED | NEXWEAVE 是独立产品，GridCrew 通过 API/事件/SDK 集成 | PRD、M-1、GridCrew 基线一致 |
| OQ-DOMAIN-001 | DECIDED | Equipment RCA 是 Domain Pack，不进入平台核心 | PRD、M-1、总纲一致 |
| OQ-GOV-001 | DECIDED | M-1 治理基线正式验收通过；M0 需单独下发 | 用户 2026-08-23 明确验收通过 |
| OQ-GOV-002 | DECIDED | 进入正式 M0，不执行 M0-Lite；完成后停止在 M0 边界 | 用户 2026-08-23 明确下发“请进入M0” |
| OQ-GOV-003 | DECIDED | M0 正式验收通过；已披露的外部 CI、容器供应链与 RustFS SPK-004 风险作为 P1 继续跟踪，M1 必须另行明确下发 | 用户 2026-08-24 明确“同意M0验收”；M0 执行报告 |
| OQ-GOV-004 | DECIDED | 上述 M0 P1 已通过远程 main CI、双架构 SBOM/CVE/Cosign 与 SPK-004 实测闭环；RustFS RC 的 HA/DR/升级规模风险转入既定 M7/M12 门禁，不再是 M0 阻塞 | 用户 2026-08-24 要求解决剩余问题；ADR-0018；GitHub Actions run 32702688049 |
| OQ-GOV-005 | DECIDED | 正式进入 M1，以 `03_NEXWEAVE_M1_平台基础、身份权限与核心领域模型任务书.md` 为边界，完成后停止 | 用户 2026-08-24 明确下发“进入 M1” |
| OQ-GOV-006 | DECIDED | M1 正式验收通过并进入 M2，以 `04_NEXWEAVE_M2_Temporal可靠知识工作流内核任务书.md` 为边界，完成后停止 | 用户 2026-08-24 明确“同意 M1 验收，进入 M2” |
| OQ-GOV-007 | DECIDED | M2 正式验收通过；用户正式下发 M3，并明确授权按 M0—M2 已验收基线完成任务书/ADR/治理校准后继续正式实施，实施后进行独立审查并停止在 M3 | 用户 2026-08-25 明确 M2 验收与 M3 下发/实施/审查顺序 |
| OQ-GOV-008 | DECIDED | 在不将 M3 标记为已验收、不开始 M4 实现的前提下，先完成 M4 语义模型治理校准，冻结 ADR、对象关系、版本权威、Pack 组合规则和 M5—M15 影响矩阵 | 用户 2026-08-29 明确指令；ADR-0022 |
| OQ-GOV-009 | DECIDED | M3 正式验收通过；本地实现、独立审查/修复、本地 P0、远程双架构 CI/SBOM/Cosign 和真实 Compose/SPK-004 证据均闭环；M4 仍未正式下发 | 用户 2026-08-29 明确“M3正式验收”；GitHub Actions run 33253911959 |
| OQ-GOV-010 | DECIDED | 正式进入 M4：先完成 M4-0 实现级决策冻结并同步 ADR/OQ/公共契约，再实施、独立审查与验收；完成后停止在 M4，不进入 M5 | 用户 2026-08-29 明确指令；ADR-0023 |
| OQ-GOV-011 | DECIDED | M4 已正式验收；用户正式下发 M5。先完成 M5-0 校准与 ADR-0024，再实施、验证并停止在 M5，不进入 M6 | 用户 2026-08-30 明确“请执行 M5”；ADR-0024 |
| OQ-GOV-012 | DECIDED | M5 已正式验收；用户正式下发并于 2026-08-31 正式验收 M6。ADR-0025、实施与验证已闭环，停止在 M6，不进入 M7 | 用户 2026-08-30 “请执行M6”、2026-08-31 “同意M6正式验收”；ADR-0025 |
| OQ-GOV-013 | DECIDED | 用户于 2026-08-31 正式下发并正式验收 M7；ADR-0026、实现与隔离真实 E2E/本地技术验收已闭环，停止在已验收 M7，不进入 M8 | 用户 2026-08-31 “请执行M7”“同意M7验收”；ADR-0026；M7 执行报告 |
| OQ-GOV-014 | DECIDED | 用户于 2026-08-31 正式下发并验收 M8；保守 Connector/Obsidian 决策、只读 Connector、Obsidian 草稿交换与 Wiki 双向链接图谱已闭环；GridCrew 集成因对端仍处规划期明确延期 | 用户 2026-08-31 “请执行M8”“同意M8验收”、确认保守默认与延期指令；ADR-0027、ADR-0028、M8 执行报告 |
| OQ-GOV-015 | DECIDED | 用户于 2026-09-01 正式下发 M9；先按 ADR-0029 完成本地 Pack。后续按 ADR-0030 建立公开 RCA 候选语料并将 GridCrew 联合试点延期；GridCrew 不再是 M9 P0，专家/阈值/真实评审仍不得静默跳过 | 用户 2026-09-01 指令；ADR-0029/0030 |
| OQ-GOV-016 | DECIDED | 用户于 2026-09-01 正式下发 M9-FE；该任务仅整治前端设计系统、信息架构和高保真原型对齐，必须保留真实 API/权限/状态语义，完成独立审查和本地验收后停止，不进入 M10 | 用户 2026-09-01 明确指令；M9-FE 任务书与前端设计系统基线 |

## M5 已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-COMPILE-001 | DECIDED | CompileJob 固定 PUBLISHED SchemaVersion/composition、SourceVersion/checksum 集、PromptVersion、ModelProfile；输入不漂移，重复 Job 不重复知识对象 | ADR-0022、0024 |
| OQ-COMPILE-002 | DECIDED | Entity/Page 稳定身份不使用标题；未知/歧义语义进入 SemanticChangeProposal 或人工映射候选，不修改当前 SchemaVersion | ADR-0022、0024 |
| OQ-MODEL-001 | DECIDED | 所有结构化生成/embedding 经 Model Gateway；调用只保存安全计量与 checksum，最高密级禁止外部模型；本地确定性 Provider 是本地验收边界，不冒充外部 LLM | ADR-0010、0015、0024 |
| OQ-WIKI-001 | DECIDED | WikiPageVersion 追加式；AI 只改 generated sections，protected sections 仅由带 ETag 的人工编辑新版本更新 | ADR-0007、0008、0024 |
| OQ-COMPILE-WF-001 | DECIDED | M2 `knowledge-compile.v1` 保留 Kernel Stub；M5 真实业务使用 v2，所有 I/O 位于幂等 Activity | ADR-0004、0020、0024 |

## M3 已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-PARSE-001 | DECIDED | 每次 reparse 创建新 ParseJob/Workflow；retry 保持同一输入配置；部分成功为 `PARTIAL_FAILED/PARTIAL` 并列出失败单元；reparse 失败不破坏既有 active 结果；文件替代创建新 SourceVersion；Anchor 固定 SourceVersion + checksum + ParseJob，重定位新建 Anchor；M2 v1 Stub 保留 Replay，M3 使用 v2。无真实 OCR Provider 时扫描 PDF 必须真实检测并明确 `OCR_REQUIRED`，不得冒充 OCR 成功 | ADR-0021；ADR-0008、0014、0018、0020；M3 正式任务书校准 |

## M3 实施中发现的权威冲突

| ID | 状态 | 问题 | 处理边界 |
|---|---|---|---|
| OQ-M3-ANCHOR-001 | DECIDED | `docs/architecture/DATA_MODEL_BASELINE.md` 第 6 节曾把 Anchor 失效结果写为 `STALE/INVALID`，与 ADR-0021 明确限定的 `VALID/STALE/UNRESOLVED/REVOKED` 及“不得使用 `INVALID`”冲突；已确认为低优先级基线残留并修正为 `STALE/UNRESOLVED/REVOKED`，不得实现 `INVALID` | M3 正式任务书；Accepted ADR-0021；主执行者 2026-08-25 按权威优先级确认并要求保留发现/修正证据 |

## M4 语义模型已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-SEMANTIC-001 | DECIDED | R1 的 Semantic Model 是 SchemaVersion 的逻辑视图；SchemaVersion 是唯一有效语义快照，不新增 OntologyVersion、独立本体状态/API 或第二发布权威 | 用户 2026-08-29 明确要求冻结；ADR-0022 |
| OQ-SEMANTIC-002 | DECIDED | 复用 EntityType/RelationType，并新增版本内 PropertyDefinition、TypeHierarchyEdge、TypeTerm、ConceptMapping、SchemaCompositionReport；stable key 跨版本识别概念，版本行 ID 不替代语义身份 | ADR-0022；Semantic Model Baseline |
| OQ-SEMANTIC-003 | DECIDED | 类型层级为无环多父图；继承约束冲突阻断。类型术语与实例 EntityAlias 分离；同名/翻译/向量相似/LLM 判断不自动表示等价 | ADR-0022 |
| OQ-SEMANTIC-004 | DECIDED | ConceptMapping 限定 EXACT/BROADER/NARROWER/RELATED；EXACT 需审核且不物理覆盖来源定义，歧义或约束不兼容时阻断 | ADR-0022 |
| OQ-SEMANTIC-005 | DECIDED | Pack 依赖解析为精确版本/checksum 并按确定性 DAG 组合；禁止后安装覆盖先安装。安装只生成 DRAFT SchemaVersion，发布独立授权；升级/禁用/回滚不删历史 | ADR-0022；ADR-0009 |
| OQ-SEMANTIC-006 | DECIDED | 编译必须先锁定 PUBLISHED SchemaVersion；编译发现的新概念只形成下一版本候选。Schema 合规不等于事实正确，不替代 Evidence | ADR-0022；ADR-0014 |
| OQ-SEMANTIC-007 | DECIDED | M4 详细校准，M5—M15 先以影响矩阵冻结强制影响，并在各 Milestone 正式下发前依据最近验收实况精确校准 | 用户 2026-08-29 明确指令；Semantic Model Impact Matrix |

## M0 已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-TECH-001 | DECIDED | 产品核心采用 Python 3.12/FastAPI；Java/CUD4.0 仅作企业适配壳 | M0 任务书 Python/TypeScript Monorepo 要求；ADR-0003、ADR-0012 |
| OQ-EXEC-001 | DECIDED | Temporal 是长任务执行权威；数据库保存业务事实与查询投影 | M0 任务书；ADR-0004 |
| OQ-IAM-001 | DECIDED | 与 GridCrew 仅保持 OIDC/服务身份协议兼容，可复用提供方但独立部署与数据 | 独立产品边界；ADR-0001、ADR-0015 |
| OQ-GW-001 | DECIDED | Model Gateway、Connector、Artifact/Evidence 先冻结兼容契约；服务复用不得改变独立权限和可用性边界 | ADR-0005、ADR-0010 |
| OQ-SOURCE-001 | DECIDED | SourceAnchor 采用绑定 SourceVersion 与 checksum 的版本化复合定位器，并含 excerpt hash 与定位状态 | ADR-0014 |
| OQ-SCHEMA-001 | DECIDED | 破坏性变更不修改历史 Release；草稿迁移形成新对象版本和影响报告 | ADR-0008、ADR-0016 |
| OQ-PACK-001 | DECIDED | 安装记录/版本不可变；卸载只禁用不删知识；升级必须显式迁移且可回滚 | ADR-0009 |
| OQ-QUERY-001 | DECIDED | R1 Query 每次只绑定一个空间内的固定 Release | ADR-0008、ADR-0016 |
| OQ-SEC-001 | DECIDED | 四级密级 PUBLIC/INTERNAL/CONFIDENTIAL/HIGHLY_RESTRICTED；最高密级禁止外部模型出域 | ADR-0015 |
| OQ-TENANT-001 | DECIDED | 从基础表开始保留 tenant_id/space_id；R1 必须验证跨租户阻断 | ADR-0013 |
| OQ-INFRA-001 | DECIDED | M0 用本机 Docker Compose 联调 PostgreSQL、RustFS、Redis、Temporal、API、Worker、Web；对象存储保持 S3/ObjectStorage Port 边界且不设置旧 Provider 回退 | 用户 2026-08-24 明确批准；ADR-0017；仅为开发基线 |
| OQ-EVID-001 | DECIDED | Claim、Relation、Evidence、Citation 分离：事实表达、结构关系、证据记录和回答引用各自独立 | ADR-0014 |
| OQ-MARKDOWN-001 | DECIDED | Markdown/Git 只作交换、展示与导出，数据库/Release 是权威状态 | ADR-0003 |
| OQ-SEARCH-001 | DECIDED | R1 默认 PostgreSQL FTS + pgvector + Relation；增加专用引擎须以测量证据和 ADR 触发 | ADR-0002 |
| OQ-RELEASE-001 | DECIDED | 空间内 SemVer + 不可变 manifest + channel pointer；回滚移动指针，不改历史版本 | ADR-0008、ADR-0016 |
| OQ-DAMENG-001 | DECIDED | 达梦/CUD4.0/国产中间件是后续适配壳，不形成第二产品核心 | ADR-0001 |

## M0 未代替业务负责人决定的事项

| ID | 状态 | 问题 | 处理边界 |
|---|---|---|---|
| OQ-METRIC-001 | DEFERRED | R1 试点引用准确率、问题覆盖率、专家接受率阈值是多少？ | 不伪造阈值；M5 前形成测量方案，M9 试点前由产品/RCA 专家批准 |
| OQ-SEC-CONTACT-001 | OPEN | 私密安全漏洞的报告联系人和响应 SLA？ | M0 可建立无联系人占位的安全流程，公开/交付前必须由安全负责人补齐 |
| OQ-LICENSE-001 | OPEN | NEXWEAVE 源代码与分发许可证采用什么策略？ | 未决定前不声明开源许可、不对外分发 |
| OQ-INFRA-002 | DECIDED | 开发机使用 Veee 全局模式恢复 Docker daemon 对 Docker Hub 官方 Registry 的访问，不引入镜像站或非官方替代源 | 用户 2026-08-24 调整网络模式；pgvector、Redis、Temporal、Python、Node、Nginx 官方镜像均已成功拉取，项目镜像构建成功；首次认证请求仍有一次 IPv6 超时，后续重试成功，继续观察稳定性 |

## P1：对应能力编码前必须决定

| ID | 状态 | 问题 | 最晚阶段 |
|---|---|---|---|
| OQ-SEMANTIC-KEY-001 | DECIDED | stable key 固定为小写 ASCII `namespace/local-name`（4—127），尾部不得为 `-`，受登记 namespace 和保留 namespace 约束；显示名称不得充当身份 | ADR-0023；M4 public contract |
| OQ-PACK-FORMAT-001 | DECIDED | v1alpha1 权威输入为 JSON-only；`RFC8785-JCS/1` 规范化，manifest/content checksum 与资源上限固定；YAML 仅可作为未来离线作者输入 | ADR-0023；M4 manifest schema |
| OQ-PACK-SIGN-001 | DECIDED | 离线 Ed25519 detached signature + 受审计 trust root + 已签名撤销清单；撤销阻断新安装但不删除历史 | ADR-0023 |
| OQ-PACK-MIGRATION-001 | DECIDED | v1alpha1 DSL 只生成预览，不执行实例数据变换；操作白名单、显式 rollback 和字节/操作预算固定 | ADR-0023 |
| OQ-PACK-UI-001 | DECIDED | R1 UI 仅允许受控 icon/color/layout/help text 声明，禁止自定义/可执行组件、远程资源和动态表达式 | ADR-0023 |
| OQ-GRID-001 | DEFERRED | GridCrew 暂不开发；Skill 的空间/Release/权限/租户映射、Webhook、SDK 和联合试点均不属于当前 M9/R1 验收 | 用户 2026-08-31、2026-09-01 明确延期；ADR-0027/0030；未来单独下发时重新开启 |
| OQ-OBSIDIAN-001 | DECIDED | 导出在 YAML frontmatter 固化页面 ID、导出基线与 checksum；无 ID 仅新草稿；回导三方 diff，所有结果进草稿/审核，基线漂移或安全/保护区变更生成 Conflict，绝不覆盖 Release | 用户 2026-08-31 确认保守默认；ADR-0027 |
| OQ-REVIEW-001 | DECIDED | 平台管理员设全局护栏，空间管理员版本化配置按风险等级的审核阶段、超时、升级、批量上限与来源权威规则；高风险固定三阶段和创建/最终批准职责分离 | ADR-0025；M6 |
| OQ-CONNECTOR-001 | DECIDED | 首期 Connector 全部最小权限只读；只允许逐实例显式的受控目录、开发 S3/RustFS、Mock REST 与本地 Git allowlist，默认拒绝外部地址/重定向/未授权路径；凭据只存审计 CredentialRef | 用户 2026-08-31 确认保守默认；ADR-0027 |
| OQ-RCA-001 | IN_PROGRESS | 9 份/610 页 NTSB 报告已准入，4 份代表性报告已完成真实 Pack→Source→Compile 技术试点；客户资料、专家名单、批准阈值和最终签署仍未提供 | ADR-0030；M9 技术试点运行证据；下一步专家确认 |

## M9 前置阻塞与延期

| ID | 状态 | 问题 | 处理边界 |
|---|---|---|---|
| OQ-M9-DATA-001 | DECIDED | 9 份公开资料已完成逐份文本/版面准入与第三方视觉元素排除；4 份跨行业代表性报告已保留 Raw、生成文本派生 SourceVersion 并候选编译 | 公开资料技术试点数据前置已关闭；不得外推为客户 IOE/LOE，也不得在专家评审前形成正式 Release |
| OQ-M9-PACK-001 | DECIDED | 真实 Pack 安装发现并修复 M4 持久化遗漏 M7 `evaluation_suites.created_by` 的跨版本缺陷；隔离租户重跑后安装 `ACTIVE` | 回归测试、Worker 重建与 M9 技术试点证据；未修改历史迁移或清理既有 Pack |
| OQ-M9-EXPERT-001 | OPEN | 尚未提供专家名单、职责、评审记录模板批准和接受率/引用准确率/覆盖率/修改比例阈值 | 可交付测量定义与空白报告；不得伪造专家确认或自行宣布达标 |
| OQ-M9-GRID-001 | DEFERRED | 用户明确 GridCrew 暂不开发，联合试点延期；对端、身份/租户映射、Skill Version、Webhook/SDK 和联合环境均不建设 | 不再是 M9 P0；保留 ADR-0001/0011 边界，未来单独下发并重新联合准入；不得以 Mock 冒充完成 |

## P2：可后置但需记录

| ID | 状态 | 问题 | 计划 |
|---|---|---|---|
| OQ-PREVIEW-001 | OPEN | 原交付说明列出的两张 PNG 预览图缺失，是否补齐？ | 不阻塞 M0，补资料包完整性 |
| OQ-MANIFEST-001 | OPEN | 原 manifest 未列出嵌套 PRD/原型文件，是否升级交付清单？ | 不改原包，在仓库 SOURCE_MANIFEST 补齐 |

## 决策记录规则

OQ-LK-D-001 / DECIDED：用户明确选择阶段 D“验收与可信边界收口”，冻结 11F / ADR-0036；优先修复已确认的 Query 历史引用不重检、重放请求不匹配和 Graph 当前节点/起点成员/预算问题，并补现有页面真实浏览器验证。工业评测仍待数据与后续范围，不进入 M10。

### OQ-FE-VISUAL-002 — DECIDED（2026-09-07，用户当前明确指令）

用户明确要求重新参考高保真原型，恢复赛博朋克科技感并重点优化交互。此决定替代上一轮前端整改任务书中弱化赛博朋克视觉的要求：恢复深墨底、紫色主操作、青色证据/导航、高层次面板；不恢复原型虚构统计、装饰性假按钮或业务 Mock。不回滚历史实现和用户修改，仅修改前端视觉/交互。继续以桌面 Web 为验收对象，不进入 M10，不改变 API、权限、证据或 Release 语义。

每个 `DECIDED` 项必须关联批准人、日期、ADR/会议记录和影响范围。若决策改变对象、状态、版本、API、事件、Workflow、SourceAnchor 或 Release 语义，必须通过 ADR，而不能只改本表。

## R1 架构收口与 R2 Living Knowledge 规划（2026-09-07）

本节由用户本次“先审查真实 Repository，再重规划 R2”的明确要求产生，只登记审查与提案，不授权 M9.5/M10 实施。设计见 [R1/R2 Review](docs/architecture/R1_CONSOLIDATION_R2_LIVING_KNOWLEDGE_REVIEW.md)，证据见 [本轮只读核查](docs/architecture/R1_CONSOLIDATION_EVIDENCE_2026-09-07.md)，ADR-0031 状态为 Proposed。已有 M9 专家/阈值/Release P0 不变。

| ID | 状态 | 待确认 / 冲突 | 处理边界 |
|---|---|---|---|
| OQ-LK-001 | OPEN | M9.5 是否作为 R1 冻结后的 R2 前置验证桥梁正式下发，其版本归属与 Go/No-Go 负责人是谁？ | 当前只交付提案；保留 R1=M0—M9、R2=M10—M12 既有归属，不以本次规划启动实现 |
| OQ-LK-002 | OPEN | 是否具备真实 P-101 身份、授权历史、测点字典/质量码、采样频率/覆盖、校准/检修记录、计划版本和数据负责人？ | 本轮未取得已确认输入；准入前不导入、不生成假曲线，不把公开事故语料或其他泵数据当 P-101 |
| OQ-LK-003 | OPEN | P-101 适用手册/规程/历史案例与固定 Release、阈值/规则/工况批准人、模型效果/误报/时延门槛是什么？ | 提供完整测量与实验方案；不得替专家填安全阈值或宣布 benchmark 达标 |
| OQ-LK-004 | PROPOSED | 现有 Schema 契约 extra=forbid，缺时序声明；新字段、Pack/Schema canonicalization 与旧客户端如何兼容？ | 采用版本化声明提案，保留旧签名/快照原字节；正式契约冻结前停止相关实现，不静默在 ui JSON 中扩展权威语义 |
| OQ-LK-005 | PROPOSED | 当前 Evidence 要求 SourceAnchor、Query 绑定固定 Release；动态引用/时间区间 Evidence/组合回答如何兼容？ | 首片独立 Observation/Forecast typed refs、DynamicAssessment；不放宽旧 Evidence/Release，直接时间 Evidence 另立 ADR 后实现 |
| OQ-LK-006 | OPEN | Provider 具体版本/部署算力/内网许可与 benchmark 候选如何冻结？ | Chronos 首发但非默认中标；TimesFM 不同版本能力与权重许可不同，必须锁版审核；无能力则拒绝，不能静默降级 |
| OQ-LK-007 | OPEN | R1 Graph 实现与 ADR-0026 的隔离/固定版本要求是否一致：节点按当前 entity ID 读取，起点成员资格、历史版本与 SQL 预截断是否充分校验？ | 记录为静态审查疑点，未执行越权利用；需针对性验证，停止相关动态图/跨空间扩展，不静默选用较宽松实现作为新基线 |
| OQ-LK-008 | OPEN | R1 当前交付工作区、运行镜像、数据库与验收环境如何固定并恢复完整闭环？ | 本轮库为 0009_m8、Release/QueryAnswer 为 0，运行列表未见业务 Worker；不否定历史隔离测试，不宣称当前可演示完整闭环 |
| OQ-LK-DOC-001 | OPEN | 较早 FRONTEND_DESIGN_SYSTEM.md 的弱化赛博视觉文字与同日已 DECIDED 的 OQ-FE-VISUAL-002 / 当前 token 不一致 | 既有 OQ 已记用户决定，规划沿用深墨/紫/青；本轮不实现样式或覆写前端文档，正式 UI 增量前校准相关文档 |

上述 OPEN/PROPOSED 不改变旧 DECIDED/Accepted 项。用户当前已授权架构审查与路线图，不需要为只读核查或本轮文档再次确认；依赖尚未确认数据/契约的实现保持停止。

### M9.5 正式开发授权更新（2026-09-07）

- OQ-LK-001：DECIDED。用户明确要求不考虑 M9 验收，先开发并运行 M9.5；覆盖此前提案的顺序限制。按 11B 任务书与 ADR-0032 执行，未下发 M10。
- OQ-LK-002/003：现场数据、专家与阈值仍 OPEN，但不阻塞真实软件/模型技术首片。开发示例显式 SYNTHETIC，可上传真实授权 CSV；不得将技术运行称为工业 Real E2E 验收。
- OQ-LK-004/005/006：首片实现选择见 ADR-0032；保留旧 Schema/Release/Evidence 语义；没有正式 Release 时动态分析明确显示缺少已发布知识依据，不能偷偷读草稿。

### M9.5 首片收尾（2026-09-08）

- OQ-LK-RUN-001 / OPEN：受控 CSV 上传完成响应曾出现 X-Trace-Id 不等于请求 traceparent 的情况；已单独留存差异，未通过该项，不为首片修改 R1 上传语义。
- OQ-LK-RUN-002 / OPEN：原计划完整 RCA/规程/历史案例检索 → 有引用 Risk Narrative 未完成。当前零适用 Release 时明确无已发布依据；有 release_id 仅验证引用，不冒充检索完成。
- OQ-LK-RUN-003 / OPEN：生产 worker 生命周期、取消/恢复、QUEUED 自动补投、配额、孤立对象清理、跨租户专项验证、实时 Connector、完整绑定向导和签名 Pack 发布仍需 M9.5 后续任务，不进入 M10。
- OQ-LK-SEC-001 / RESOLVED FOR LOCAL SLICE：初始可选推理依赖审计发现 13 个通告；Torch 升至 2.13.0，Transformers 升至 5.10.4，重新审计完整 lock 无已知漏洞并真实复跑成功。该结论不等于生产安全/供应链认证。
- OQ-LK-UI-001 / FIXED：空间选择器只加载首 50 项导致新建演示空间不可见；已沿用现有 cursor API 完成分页并加回归测试。Graph 首片是来源链视图，Ask 首片是结构化条件预测，不宣称完整自由文本查询/图谱投影已升级。

### 阶段 A 稳定基础更新（2026-09-09）

- 用户于 2026-09-08 明确下发阶段 A，11C / ADR-0033 已建立；无需再次确认常规本地修复和隔离软件验收。
- OQ-LK-008：本地运行恢复和完整 R1 **软件闭环部分已解决**。统一启动、可选预测 worker、持久投递/取消/重跑、版本与追踪隔离完成；真实 API 在独立合成空间完成 Source→Compile→Review→Release→Query/rollback。既有工作区尚未由用户提交冻结，远程 CI/生产环境和工业验收不因此关闭。
- OQ-LK-A-001：RESOLVED。真实演练发现 PostgreSQL 无法推断可空投递错误参数的类型；已显式类型转换，并将实际适配器 SQL 的 NULL/非 NULL 路径加入隔离迁移检查。
- OQ-LK-A-002：DECIDED（实现限制按 ADR-0033 留痕）。取消阻止制品发布，不承诺立即中断 CPU；已启动 Workflow 最长 20 分钟，worker 离线超时后显式失败，恢复后可用原输入创建新任务。整机重启/进程强杀后通过统一入口恢复，不将本地 supervisor 冒充生产常驻服务。
- OQ-LK-002/003/005/007 及 M9 原有专家、批准阈值、固定版本 Graph 隔离疑点仍开放。阶段 A 没有新增工业数据、已发布 RCA 引用合成或动态图语义，也未进入阶段 B/M10。

### 阶段 B 范围冻结（2026-09-09）

后续授权：用户已明确下发阶段 C。OQ-LK-C-001 / DECIDED：按 ADR-0033 的知识引用深化、原始 M9.5 目标和 B 遗留项，冻结 11E/ADR-0035；实施同空间固定 Release 回接，不扩展为工业评测或 M10。阶段 C 结果是独立读时组合，不回写旧预测。

OQ-LK-B-001 / DECIDED：依据既定“用户自主运行”阶段及用户明确下发，11D/ADR-0034 将 B 限定为已有已发布时序 Schema、知识对象和受控 CSV 上的绑定/预检/运行/比较；从零领域建模、工业评测、签名 Pack 和 RCA 引用合成保持后续范围。前置资源不足时指向既有治理页面，不提供平台内置设备分支。

OQ-LK-B-002 / RESOLVED：复核发现预测适配器原先只排除 SourceVersion 状态，遗漏 R1 的独立 `source_invalidations` 权威记录。B 按 ADR-0034 补充 CSV 预览/绑定与预测前、提交前的失效门禁，拒绝归档资料；不修改 R1 Source 状态模型或旧制品。需以单元和真实失效源 API 负向检查留证。

OQ-LK-B-003 / RESOLVED：真实资料选择暴露 R1 Source 列表/详情/归档响应含未声明 archived_at，引发契约 500。按原 SourceDocumentResponse 收口返回投影，保留数据库归档时间，真实 API 列表/详情/归档验证留证；没有放宽 extra=forbid。

### 阶段 C 本地技术收尾（2026-09-09）

OQ-LK-RUN-002 / PARTIALLY RESOLVED：固定 Release 的软件引用回接已实现并真实验证，含原文定位、跨空间/越权拒绝、失效源移除与旧预测不变；相关材料不代表当前设备适用性或因果。真实工业 RCA/规程/案例、专家审核及自动专业风险解释仍待后续验证。

OQ-LK-C-002 / DISCLOSED：本轮接口对返回支持材料重做门禁，不代表旧 R1 Query/Graph 的所有历史接口已完成隔离复核；旧 OQ-LK-007 不关闭。读时结果标记核验时间，源后续变化需要再次检索。当前没有完整浏览器点击/视觉验收或工业 Benchmark。

阶段 B 收尾验证：B-002 已通过单元与真实失效源预览/预检/保存三项 409 拒绝；B-003 还包含嵌套版本 object_key 的公开投影修复，真实列表、CSV 筛选、详情和归档均通过，内部存储字段未暴露。证据见 `阶段B_运行证据.json`。B 已完成本地技术验证；阶段 C/M10、工业评测、RCA 引用合成及旧 Graph 隔离疑点不因此关闭。
