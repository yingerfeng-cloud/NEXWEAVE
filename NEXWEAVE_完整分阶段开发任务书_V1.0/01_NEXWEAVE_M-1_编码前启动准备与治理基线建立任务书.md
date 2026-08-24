# NEXWEAVE M-1：编码前启动准备与治理基线建立任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 阶段：M-1（编码前准备，不进入功能开发）  
> 执行对象：Codex  
> 上位基线：NEXWEAVE PRD V1.0、高保真交互原型 V1.0、GridCrew 终局架构与开发治理基线  
> 执行原则：资料先行、契约先行、架构先行、证据与版本内建、平台与领域解耦

---

## 1. 任务背景

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台。平台负责将 PDF、Word、Markdown、业务记录等原始资料持续编译为可阅读、可链接、可审核、可追溯、可发布、可由业务系统调用的可信知识资产。

NEXWEAVE 与 GridCrew 的关系已明确：

- GridCrew 是数字员工协作、任务编排与执行平台；
- NEXWEAVE 是可信知识生产、审核、版本发布与知识服务平台；
- 两者保持独立产品形态，通过 API、事件与 Domain Pack/Skill 映射集成；
- 不允许将 NEXWEAVE 写成 GridCrew 内部的场景模块，也不允许复制形成第二套知识内核。

当前已完成：

1. `NEXWEAVE_LLM_Wiki标准化平台_PRD_V1.0.md`；
2. `NEXWEAVE_高保真交互原型_V1.0.html`；
3. 原型预览图与交付说明；
4. 产品定位、16 个一级模块、核心对象、MVP 与 M0—M4 路线已初步定义。

本阶段不得直接开发资料中心、编译中心、Wiki、Schema、审核、发布、问答等功能。M-1 的目标是把后续 M0 所需的上位资料、仓库治理、架构边界、核心术语、追踪体系和开放问题准备完整。

---

## 2. 本阶段目标

M-1 必须完成以下目标：

1. 建立唯一、清晰、可审计的产品资料目录；
2. 初始化 Git 仓库和工程治理规则；
3. 固化 NEXWEAVE 与 GridCrew 的产品边界；
4. 建立核心领域对象、状态、版本、租户和证据概念的初始基线；
5. 建立后续 M0 所需的 ADR、需求追踪、接口清单和开放问题；
6. 建立项目命名、目录、依赖和安全红线；
7. 识别 PRD、原型和拟定技术路线之间的冲突与缺口；
8. 输出可供下一阶段直接使用的仓库与文档基线。

M-1 完成后必须停止，不得自行进入 M0，不得生成 M0 正式任务书。

---

## 3. 强制上位资料

执行前先在项目根目录核查并归档以下资料。若文件名略有差异，可以按实际文件识别，但不得改写原文内容。

### 3.1 NEXWEAVE 产品资料

建议归档至 `docs/product/nexweave/`：

- `NEXWEAVE_LLM_Wiki标准化平台_PRD_V1.0.md`
- `NEXWEAVE_高保真交互原型_V1.0.html`
- `NEXWEAVE_原型预览.png`
- `NEXWEAVE_Schema预览.png`
- `README_交付说明.md`

### 3.2 GridCrew 对齐资料

若项目目录中已提供，归档至 `docs/reference/gridcrew/`：

- GridCrew 终局架构与产品版本路线 PRD；
- GridCrew 终局架构与分版本完整开发计划；
- GridCrew Codex 开发任务书统一命名基线；
- GridCrew M-1 编码前启动准备与治理基线任务书；
- GridCrew 的核心对象、Skill/Tool/Connector、Artifact/Evidence、权限、审计与版本规范。

GridCrew 资料仅作为共享架构原则和集成契约参考，不得覆盖 NEXWEAVE 的独立产品定位。

### 3.3 原始需求资料

若存在设备 RCA 技术规范、业务需求说明书或其他试点资料，归档至：

```text
docs/reference/domain/rca/
```

这些资料属于首发 Domain Pack 的业务输入，不得进入平台核心对象命名。

---

## 4. 不可变产品与架构原则

本阶段必须在 `ARCHITECTURE_BASELINE.md` 中写入以下不可变原则。

### 4.1 产品边界

1. NEXWEAVE 是独立的企业可信知识平台，不是 GridCrew 子模块；
2. GridCrew 通过正式 Knowledge API、事件或 SDK 消费已发布知识；
3. NEXWEAVE 不负责群聊、数字员工排班、任务协作和通用 Agent 执行；
4. GridCrew 不直接写入 NEXWEAVE 正式知识，只能提交资料、反馈、案例草稿、冲突线索或审核任务；
5. 业务系统只允许消费正式 Release，不得默认消费草稿知识；
6. Obsidian 是可选专家客户端，不是平台本体，不是权威状态源。

### 4.2 知识可信原则

1. Raw First：原始资料不可被 LLM 覆盖；
2. Schema Before Generation：先有 Schema，再有知识编译；
3. Evidence Native：正式 Claim 与因果 Relation 必须绑定 Evidence；
4. Human in the Loop：正式知识必须经过人工审核；
5. Draft/Release Separation：草稿与正式知识严格隔离；
6. Conflict Instead of Overwrite：冲突生成对象，不静默覆盖；
7. Version Reproducibility：历史回答能够还原知识版本、模型和 Prompt；
8. AI 生成不等于知识，只有审核发布后才成为正式知识资产。

### 4.3 平台与领域解耦

1. 平台核心不得写死设备、泵、轴承、振动、RCA、消防、合同等行业概念；
2. Domain Pack 通过声明式 Schema、模板、术语、提示词、规则和评测集扩展；
3. 场景包不得直接修改平台核心数据库结构和服务逻辑；
4. 所有 Domain Pack 必须有独立版本、依赖声明、兼容范围和安装记录；
5. Equipment RCA Pack 是首发验证包，不是平台内核。

### 4.4 集成与执行原则

1. 模型调用必须经统一 Model Gateway，不允许业务代码直接绑定模型厂商 SDK；
2. 外部资料源和业务系统必须经 Connector 接入；
3. 长时间编译、解析、评估、发布和人工审核流程必须使用可靠工作流机制；
4. 工作流定义中不得直接执行不确定网络、模型、数据库或文件操作；外部操作必须放入可重试、可观测、幂等的 Activity/Task；
5. API、事件、对象 ID、状态和版本语义必须先冻结再编码；
6. 不得建立与 GridCrew 冲突的第二套 Artifact、Evidence、Approval、Model Gateway 或 Connector 基础语义。

---

## 5. 技术路线初始基线

M-1 只形成建议基线和待决策项，不进行大规模依赖安装。若上位资料未明确，按以下路线写入技术决策候选，并在 M0 通过 ADR 正式冻结。

### 5.1 推荐产品核心栈

为降低与 GridCrew 的集成成本，优先采用同一技术族：

- Monorepo；
- Web：React + TypeScript；
- API/领域服务：Python + FastAPI + Pydantic + SQLAlchemy + Alembic；
- 可靠工作流：Temporal + Python SDK；
- Agent/LLM 编排：独立编译 Worker，通过 Model Gateway 调用模型；
- 关系数据库：PostgreSQL；
- 向量能力：pgvector，保留 Milvus 适配接口；
- 对象存储：MinIO/S3；
- 缓存与短任务协调：Redis；
- 搜索：先定义 Search Provider 接口，MVP 可从 PostgreSQL 全文检索起步，后续接 OpenSearch；
- 图谱：MVP 使用类型化 Relation 表与图遍历服务，不在首期强制部署 Neo4j；
- 身份认证：OIDC，保持与 GridCrew/Keycloak 兼容；
- 可观测性：OpenTelemetry；
- 本地开发：Docker Compose；
- 正式部署：Kubernetes 兼容，私有化优先。

### 5.2 企业适配边界

对于要求 Java/CUD4.0、达梦数据库或国产中间件的客户项目：

- 通过部署适配、数据库适配、API 网关或企业集成壳实现；
- 不在产品核心中复制第二套知识引擎；
- 是否使用 Java 作为客户侧应用壳，在 M0 ADR 中单独决策；
- 不得因单一客户要求将 CUD、达梦或核电专用逻辑写入平台核心领域层。

### 5.3 本阶段必须形成的技术 Spike 清单

仅形成设计与验证计划，不完成正式业务代码：

1. Temporal 是否作为 NEXWEAVE 编译、审核、发布唯一可靠工作流内核；
2. PostgreSQL + pgvector 是否能满足 MVP 的文本、向量和关系查询；
3. Markdown/YAML 与数据库权威状态的边界；
4. Source 文件版本、checksum 与 MinIO 对象模型；
5. PDF/Word/Markdown 解析器的插件接口；
6. Claim/Evidence 精确定位到页码、段落和字符范围的可行性；
7. Domain Pack 声明格式和兼容策略；
8. NEXWEAVE 与 GridCrew 的 Knowledge Pack → Skill 映射方式。

---

## 6. 统一工程命名基线

在 `docs/governance/NAMING_BASELINE.md` 中固定以下命名。

| 对象 | 统一命名 | 约束 |
|---|---|---|
| 产品 | NEXWEAVE / NEXWEAVE 企业级 LLM Wiki 标准化平台 | UI 可展示“织界” |
| 代码仓库 | `nexweave` | 禁止使用 `rca-wiki` 等场景名 |
| Python 根包 | `nexweave` | 领域包不得成为根包 |
| 前端 Scope | `@nexweave/*` | 公共 UI、contracts、sdk 统一命名 |
| 环境变量 | `NEXWEAVE_*` | 密钥只保存引用 |
| Docker 镜像 | `nexweave-web`、`nexweave-api`、`nexweave-worker-*` | 语义化版本 |
| Temporal Namespace | `nexweave-dev/test/prod` | 按环境隔离 |
| Temporal Task Queue | `nexweave.compile.default`、`nexweave.review.default`、`nexweave.release.default` | 不使用客户专用硬编码 |
| OpenTelemetry Service | `nexweave.web`、`nexweave.api`、`nexweave.worker.*` | 日志、指标、Trace 统一命名族 |
| Domain Pack | `<domain-id>-pack` | 如 `equipment-rca-pack` |
| API Prefix | `/api/v1` | 版本化，不使用无版本接口 |

---

## 7. 建议仓库结构

M-1 只建立目录、说明和最小配置，不实现功能。

```text
nexweave/
├── AGENTS.md
├── README.md
├── ARCHITECTURE_BASELINE.md
├── PRODUCT_BASELINE.md
├── OPEN_QUESTIONS.md
├── pyproject.toml                 # 可仅建立工作区基线
├── package.json                   # 可仅建立前端工作区基线
├── .editorconfig
├── .gitignore
├── .env.example
├── docs/
│   ├── product/
│   │   └── nexweave/
│   ├── reference/
│   │   ├── gridcrew/
│   │   └── domain/rca/
│   ├── architecture/
│   │   ├── DOMAIN_MODEL_BASELINE.md
│   │   ├── DATA_MODEL_BASELINE.md
│   │   ├── API_CONTRACT_BASELINE.md
│   │   ├── EVENT_CONTRACT_BASELINE.md
│   │   ├── WORKFLOW_BASELINE.md
│   │   ├── DOMAIN_PACK_SPEC_DRAFT.md
│   │   ├── GRIDCREW_INTEGRATION_BASELINE.md
│   │   └── adr/
│   ├── governance/
│   │   ├── NAMING_BASELINE.md
│   │   ├── REQUIREMENT_ID_BASELINE.md
│   │   ├── REQUIREMENTS_TRACEABILITY_MATRIX.md
│   │   ├── SECURITY_BASELINE.md
│   │   ├── QUALITY_GATES.md
│   │   └── DEVELOPMENT_WORKFLOW.md
│   └── spikes/
│       └── SPIKE_BACKLOG.md
├── apps/
│   ├── web/
│   └── api/
├── workers/
│   ├── compile/
│   ├── parse/
│   ├── evaluate/
│   └── release/
├── packages/
│   ├── domain/
│   ├── contracts/
│   ├── sdk/
│   ├── ui/
│   └── domain-pack-sdk/
├── domain-packs/
│   └── equipment-rca/
├── infra/
│   ├── compose/
│   ├── temporal/
│   └── observability/
└── tests/
    ├── architecture/
    ├── contracts/
    └── fixtures/
```

目录可以根据实际包管理工具小幅调整，但必须保留以下边界：

- `domain` 与 `contracts` 不依赖 FastAPI、数据库、Temporal、模型 SDK；
- Workflow 只依赖确定性代码与契约；
- Worker 通过 Gateway/Port 调用外部能力；
- Domain Pack 只能注册声明、模板和扩展点，不依赖平台内部实现；
- GridCrew 集成代码放在 Integration/SDK 层，不进入核心领域对象。

---

## 8. 必须创建的治理文件

### 8.1 `AGENTS.md`

必须至少规定：

- 上位资料优先级；
- 不得自行改变产品边界；
- 不得自行进入下一 Milestone；
- 修改核心对象、状态、版本、API 和事件必须先写 ADR；
- 不得引入客户或 RCA 专用核心分支；
- 不得绕过 Model Gateway、Connector、权限、审计、Evidence 和 Release；
- AI 生成代码必须配套测试和文档；
- 未确认的需求进入 `OPEN_QUESTIONS.md`，不得静默假设；
- 不得伪造 Git 用户身份或提交记录；
- 用户已有未提交修改不得覆盖或重置。

### 8.2 `PRODUCT_BASELINE.md`

必须包括：

- 一句话定位；
- 产品不是；
- 标准平台 + Domain Pack + Business App 三层结构；
- 16 个一级功能域；
- MVP 范围与暂不建设范围；
- NEXWEAVE 与 GridCrew 的边界；
- 首发 Equipment RCA Pack 的验证目标。

### 8.3 `ARCHITECTURE_BASELINE.md`

必须包括：

- 系统上下文图；
- 容器级架构草图；
- 核心服务边界；
- 平台与领域包依赖规则；
- 草稿/正式知识隔离；
- Source、Evidence、Release 的权威状态；
- Model Gateway、Connector、Workflow、Audit 边界；
- 与 GridCrew 的集成位置；
- 当前未冻结决策。

### 8.4 `DOMAIN_MODEL_BASELINE.md`

必须定义但暂不实现以下核心对象：

- Tenant / Organization / User / ServiceIdentity；
- KnowledgeSpace；
- SourceDocument / SourceVersion；
- ParseJob；
- SchemaDefinition / SchemaVersion；
- EntityType / RelationType / PageTemplate；
- WikiPage / WikiPageVersion；
- Entity / EntityAlias；
- Relation；
- Claim；
- Evidence；
- Conflict；
- CompileJob / CompileStep；
- ReviewTask / ReviewAction / Approval；
- EvaluationSuite / EvaluationRun；
- Release / ReleaseItem；
- DomainPack / DomainPackVersion / Installation；
- Connector / ModelProfile / PromptVersion；
- QuerySession / QueryAnswer / Citation；
- AuditLog。

每个对象至少写明：

- 业务含义；
- 唯一 ID；
- 所属租户/空间；
- 版本策略；
- 生命周期状态；
- 与其他对象关系；
- 权威状态源；
- 是否允许 AI 创建；
- 是否必须人工审核。

### 8.5 `DATA_MODEL_BASELINE.md`

必须包含：

- PRD 核心表清单；
- 所有业务表的租户、空间、版本、审计字段策略；
- Source hash、对象存储 key、文件版本关系；
- Wiki 不可覆盖式版本；
- Claim/Evidence 强约束；
- Release 不可变原则；
- Outbox/Event Log 初始设计；
- PostgreSQL/达梦适配风险；
- pgvector 与图关系表的边界。

不要求生成正式 Alembic 迁移，但应给出 ER 草图或 Mermaid 图。

### 8.6 `DOMAIN_PACK_SPEC_DRAFT.md`

至少定义：

- `manifest`；
- pack ID、版本、平台兼容范围；
- 实体类型；
- 关系类型；
- 页面模板；
- 术语与同义词；
- 编译提示词；
- 审核规则；
- Lint 规则；
- 标准问题集；
- 示例数据；
- 前端扩展声明；
- 安装、升级、卸载和回滚；
- 禁止执行任意代码的安全原则。

同时提供 `equipment-rca-pack` 的最小声明示例，但不得实现 RCA 诊断逻辑。

### 8.7 `GRIDCREW_INTEGRATION_BASELINE.md`

必须写清：

- GridCrew → NEXWEAVE：知识查询、证据读取、关系遍历、版本查询、编译任务提交、反馈/案例草稿提交；
- NEXWEAVE → GridCrew：知识发布事件、审核任务通知、冲突通知、知识包更新事件；
- Knowledge Pack → GridCrew Skill 的映射原则；
- 两个平台共享和不共享的对象；
- 身份透传、租户、权限和审计边界；
- 幂等、重试和错误码；
- GridCrew 不得绕过 Release 查询草稿知识；
- 首期只读集成，后续知识回流的阶段策略。

### 8.8 `API_CONTRACT_BASELINE.md`

基于 PRD API 草案，按资源域形成接口清单：

- spaces；
- sources；
- schemas；
- compile jobs；
- wiki pages；
- entities/relations；
- claims/evidence；
- conflicts；
- reviews/approvals；
- evaluations；
- releases；
- queries；
- domain packs；
- connectors；
- GridCrew integration。

每项至少包含：

- 方法与路径；
- 调用方；
- 权限；
- 幂等策略；
- 主要输入输出对象；
- 同步/异步；
- 状态码和错误语义；
- 是否属于 M1/M2/M3/M4。

本阶段不实现 API。

### 8.9 `WORKFLOW_BASELINE.md`

至少定义候选 Workflow：

- SourceIngestionWorkflow；
- KnowledgeCompileWorkflow；
- HumanReviewWorkflow；
- QualityEvaluationWorkflow；
- KnowledgeReleaseWorkflow；
- DomainPackInstallWorkflow；
- GridCrewFeedbackIngestionWorkflow。

每个 Workflow 写明：

- 业务目标；
- Workflow ID 规则；
- 输入输出；
- Activity 边界；
- Signal/Update；
- 超时、重试、补偿、取消；
- 幂等键；
- 权威状态与数据库投影关系。

### 8.10 `SECURITY_BASELINE.md`

必须包括：

- 多租户与知识空间隔离；
- Raw、Draft、Release 的访问边界；
- 文件密级和模型调用策略；
- 高密资料禁止外部模型访问；
- API、OIDC、服务身份；
- RBAC + ABAC 初始模型；
- 敏感字段与密钥；
- 审计、下载、水印、导出控制；
- Prompt 注入、恶意文档、文件解析安全；
- Domain Pack 供应链安全；
- 依赖与许可证清单要求。

### 8.11 `QUALITY_GATES.md`

至少定义：

- 文档门禁；
- 架构门禁；
- 契约门禁；
- 安全门禁；
- 代码门禁；
- 测试门禁；
- 发布门禁；
- 知识质量门禁。

明确：M0 未通过不得进入 M1；核心对象、状态、版本、Workflow 和 API 未冻结不得进行功能编码。

### 8.12 `REQUIREMENTS_TRACEABILITY_MATRIX.md`

将 PRD 的 16 个一级模块、MVP 14 项能力和非功能需求建立唯一需求 ID，例如：

```text
NXW-SPACE-001
NXW-SOURCE-001
NXW-COMPILE-001
NXW-WIKI-001
NXW-SCHEMA-001
NXW-CLAIM-001
NXW-REVIEW-001
NXW-RELEASE-001
NXW-QUERY-001
NXW-INTEGRATION-001
NXW-NFR-SEC-001
```

矩阵至少包含：

- 需求 ID；
- 需求来源；
- 原型页面；
- Milestone；
- 核心对象；
- API；
- 测试类型；
- 状态；
- 备注。

---

## 9. ADR 初始清单

在 `docs/architecture/adr/` 建立以下 ADR 草案。M-1 可保持 Proposed 状态，不得伪装成已批准。

1. ADR-0001：NEXWEAVE 独立产品与 GridCrew API 集成；
2. ADR-0002：Monorepo 与模块化单体 + 独立 Worker；
3. ADR-0003：Python/FastAPI 作为产品核心后端候选；
4. ADR-0004：Temporal 作为可靠知识工作流候选；
5. ADR-0005：PostgreSQL + pgvector 作为 MVP 统一数据基座；
6. ADR-0006：关系表优先、图数据库后置；
7. ADR-0007：数据库为正式业务权威状态，Markdown 为可交换知识表示；
8. ADR-0008：Raw/Draft/Release 分层与不可变 Release；
9. ADR-0009：Domain Pack 声明式扩展；
10. ADR-0010：统一 Model Gateway 与 Connector SPI；
11. ADR-0011：GridCrew Knowledge Pack → Skill 映射；
12. ADR-0012：企业 Java/CUD4.0 适配壳而非第二套内核。

每个 ADR 包含：背景、决策问题、候选方案、推荐方案、正反影响、迁移风险、待验证项、状态。

---

## 10. Git 与仓库治理

### 10.1 Git 初始化

- 若目录尚未初始化，执行 `git init`；
- 不得伪造 `user.name` 或 `user.email`；
- 若 Git 身份未配置，保留未提交状态并在总结中说明；
- 不得重置、覆盖或删除用户已有文件；
- 不得自动 push 或创建远程仓库；
- 不得自动进入功能开发分支。

### 10.2 基础文件

创建：

- `.gitignore`；
- `.editorconfig`；
- `.gitattributes`；
- `.env.example`，仅允许占位符；
- `LICENSES/README.md` 或等价第三方依赖治理说明；
- `CODEOWNERS` 草案；
- `CONTRIBUTING.md`；
- `SECURITY.md`；
- `CHANGELOG.md` 初始文件。

### 10.3 凭据与敏感信息

- 不得把任何 API Key、密码、Cookie、内部地址写入仓库；
- 原型和演示数据不得包含真实核电项目敏感信息；
- `.env.example` 只写变量名和说明；
- 文档中的示例设备、人员和组织使用虚构或脱敏值。

---

## 11. M-1 禁止事项

本阶段严禁：

1. 开发真实登录、空间、资料、编译、Wiki、审核、发布或问答功能；
2. 实现 LLM 调用、OCR、向量检索、知识图谱或 RCA 算法；
3. 部署或引入大量生产依赖；
4. 生成正式数据库迁移并声称核心表已冻结；
5. 将原型 HTML 直接拆成生产前端并视为功能完成；
6. 把设备/RCA 字段写入平台核心领域对象；
7. 将 NEXWEAVE 合并进 GridCrew 单体仓库；
8. 建立与 GridCrew 重复的 Model Gateway、Evidence、Artifact、Approval 或 Connector 语义；
9. 以关键词规则替代 Domain Pack 与 Schema 机制；
10. 自行修改 PRD、原型和产品名称；
11. 自行生成 M0 正式任务书或进入 M0；
12. 在 Git 身份未配置时伪造提交。

---

## 12. 执行步骤

### 步骤 1：环境与资料盘点

- 输出现有目录树；
- 识别 NEXWEAVE 与 GridCrew 上位资料；
- 识别 Git 状态、未提交文件和现有工程；
- 识别命名冲突、重复文件和缺失资料；
- 不修改用户原始资料内容。

### 步骤 2：资料归档与索引

- 按第 3 章归档资料；
- 创建 `docs/INDEX.md`；
- 记录每份资料的名称、版本、用途、优先级和是否为权威基线；
- 标记过期、重复或仅供参考的文件。

### 步骤 3：建立仓库治理

- Git 初始化；
- 创建治理基础文件；
- 建立统一命名和目录；
- 创建 AGENTS.md。

### 步骤 4：提炼产品与架构基线

- 从 PRD 和原型提炼，不得自行扩充业务功能；
- 建立 PRODUCT_BASELINE、ARCHITECTURE_BASELINE；
- 明确 NEXWEAVE 与 GridCrew 边界；
- 标记所有尚未决定的问题。

### 步骤 5：建立核心契约草案

- 领域模型；
- 数据模型；
- API 清单；
- 事件清单；
- Workflow 清单；
- Domain Pack 规范；
- GridCrew 集成基线。

### 步骤 6：建立质量、安全与追踪体系

- 需求 ID；
- 追踪矩阵；
- 质量门禁；
- 安全基线；
- Spike backlog；
- Open questions。

### 步骤 7：一致性检查

至少检查：

- PRD、原型与领域对象是否一致；
- 16 个一级模块是否全部进入追踪矩阵；
- MVP 14 项能力是否都有 Milestone；
- Raw、Draft、Release 是否存在双重权威；
- Claim、Evidence、Relation、Citation 是否语义重复；
- Review、Approval、Release 是否边界清楚；
- Domain Pack 是否可能侵蚀平台核心；
- 与 GridCrew 是否存在对象或状态冲突；
- 技术栈是否存在不可兼容或重复建设风险。

### 步骤 8：输出总结并停止

按第 15 章模板输出，不得继续 M0。

---

## 13. 最低验收标准

M-1 通过必须同时满足：

### 13.1 资料与仓库

- [ ] NEXWEAVE PRD、原型和说明已归档；
- [ ] GridCrew 参考资料已归档或明确缺失；
- [ ] Git 状态已说明；
- [ ] 未覆盖用户原始文件；
- [ ] AGENTS.md 已建立；
- [ ] 目录和命名统一。

### 13.2 产品与架构

- [ ] 产品边界、非目标和 MVP 已提炼；
- [ ] NEXWEAVE 与 GridCrew 分工清晰；
- [ ] 核心对象清单完整；
- [ ] Raw/Draft/Release 权威关系清晰；
- [ ] Domain Pack 与核心平台解耦；
- [ ] 技术决策均处于明确状态，不得用模糊描述掩盖未决问题。

### 13.3 契约与治理

- [ ] API、事件、Workflow 和数据模型有初始清单；
- [ ] 需求 ID 与追踪矩阵覆盖 PRD 一级模块和 MVP；
- [ ] 安全与质量门禁完整；
- [ ] ADR 清单已建立；
- [ ] 技术 Spike 有验证目标和通过标准；
- [ ] OPEN_QUESTIONS.md 不少于实际发现的问题，且未静默做关键假设。

### 13.4 停止条件

- [ ] 未实现业务功能；
- [ ] 未自行进入 M0；
- [ ] 未自行生成 M0 任务书；
- [ ] 已输出 M-1 结论与 M0 输入清单。

---

## 14. 重点开放问题

执行过程中必须核查并记录，禁止自行拍板：

1. NEXWEAVE 产品核心是否正式采用 FastAPI，还是 Java/Spring Boot；
2. 是否与 GridCrew 共用 IAM、Model Gateway、Artifact/Evidence 契约或仅兼容；
3. Temporal 是否是所有长任务和人工审核的唯一状态权威；
4. Markdown/Git 与数据库各自承担什么权威角色；
5. Claim、Relation、Evidence、Citation 的最小不可重复语义；
6. Source 的页码、段落、bbox、字符范围如何统一定位；
7. 资料解析失败、部分成功和重新解析如何版本化；
8. Schema 变更如何影响已有 Wiki、Claim 与 Release；
9. Domain Pack 是否允许前端组件扩展，允许到什么程度；
10. Pack 升级如何迁移已有知识；
11. Query 是否允许混用多个 Release；
12. GridCrew Skill 如何绑定知识包版本和权限；
13. 高密级资料如何选择模型与隔离推理环境；
14. 国产化/达梦/CUD4.0 适配属于产品核心还是交付适配层；
15. MVP 搜索是否需要 OpenSearch，还是 PostgreSQL 足够；
16. 是否需要在 M1 就支持多租户，还是先实现单部署多空间但保留 tenant_id。

---

## 15. Codex 最终回报格式

完成后严格按以下格式回报：

```markdown
# NEXWEAVE M-1 执行结果

## 1. 总体结论
- M-1：通过 / 有条件通过 / 不通过
- 是否可以进入 M0：是 / 否
- Git 基线：已提交 / 未提交及原因

## 2. 实际执行内容
- 资料归档：
- 仓库治理：
- 架构基线：
- 领域与数据模型：
- API/事件/Workflow：
- Domain Pack：
- GridCrew 集成：
- 安全与质量：
- 需求追踪：

## 3. 新增或修改文件
逐项列出文件路径及用途。

## 4. 关键决策与未决项
- 已明确：
- Proposed ADR：
- 必须由用户/架构负责人决定：

## 5. 一致性检查结果
- PRD ↔ 原型：
- PRD ↔ 领域模型：
- NEXWEAVE ↔ GridCrew：
- 平台 ↔ Domain Pack：
- 权威状态与版本：

## 6. 风险与阻塞
按 P0/P1/P2 分类。

## 7. M0 输入是否齐备
- 已齐备：
- 仍缺失：

## 8. 验证命令与结果
仅列实际执行的命令和真实结果。

## 9. 停止声明
已按任务书停止在 M-1，未进入 M0，未实现业务功能，未生成 M0 正式任务书。
```

---

## 16. 交付判定

本任务的成功标准不是“生成很多文档”，而是：

> PRD、原型、领域对象、数据、Workflow、API、Domain Pack 与 GridCrew 集成之间形成一套无明显冲突、可追踪、可评审的编码前基线，使正式 M0 能够在不返工产品内核的前提下冻结架构并建立工程骨架。

M-1 完成后必须停止，等待用户将 Codex 执行结果交回，由产品/架构负责人编制 NEXWEAVE M0 正式任务书。
