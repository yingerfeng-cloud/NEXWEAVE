# GridCrew M-1：编码前启动准备与治理基线建立任务书

## 0. 任务定位

你正在处理的项目是 **GridCrew 电力行业数字员工平台**。

本任务是正式研发开始前的 **M-1编码前启动准备阶段**，目标是把当前项目资料目录整理成一个可长期维护、可由Codex持续开发、可审计、可追踪且不易发生架构漂移的Git工程基线。

本任务完成后才能进入：

> GridCrew M0：终局架构冻结与工程骨架建设

本任务**不是M0本身**，不得提前创建完整应用工程、开发业务功能或实现页面。

---

## 1. 当前已知输入

项目根目录当前包含或应包含以下资料：

1. GridCrew高保真原型V2.2目录；
2. GridCrew终局架构与产品版本路线PRD V2.2；
3. GridCrew终局架构与分版本完整开发计划V2.2；
4. GridCrew Codex开发任务书统一命名基线；
5. README或交付说明。

你必须先检查实际文件名、目录和文件内容，以实际工程为准，不得假设文件一定与上述名称完全一致。

---

## 2. 开工前强制要求

开始修改前，必须依次完成：

1. 输出当前根目录文件树；
2. 检查当前目录是否已经是Git仓库；
3. 检查是否存在未提交修改、已有分支或已有提交；
4. 检查所有源资料能否打开和读取；
5. 阅读PRD、开发计划、原型README和命名基线；
6. 总结你理解的产品定位、R1边界和不可变架构约束；
7. 给出本任务的简短执行计划；
8. 确认不会修改源Word文档和原型业务内容后，再开始执行。

如发现资料缺失、文件损坏、无法读取、版本冲突或工程已存在代码，先停止并报告，不得自行猜测。

---

## 3. 本任务的核心目标

完成以下七项工作：

1. 整理项目目录；
2. 初始化或核查Git基线；
3. 创建根目录`AGENTS.md`；
4. 创建架构与治理基线文档；
5. 创建GridCrew R1开发任务总纲；
6. 创建GridCrew M0终局架构冻结与工程骨架任务书；
7. 建立需求、术语、架构决策和源资料追踪机制。

完成后，项目应具备：

- 唯一明确的产品资料来源；
- 唯一明确的架构约束；
- Codex长期工作规则；
- R1完整路线；
- 可直接执行的M0任务书；
- 源资料完整性记录；
- 可追踪的需求与架构决策；
- 清晰的下一步开发入口。

---

## 4. 严格任务边界

### 4.1 本轮必须完成

- 目录整理；
- Git初始化或Git状态核查；
- 根目录治理文件；
- `AGENTS.md`；
- 架构基线；
- 初始ADR；
- 术语表；
- 需求追踪矩阵；
- R1任务总纲；
- M0任务书；
- 文档索引；
- 源文件清单和校验值；
- 基础验证脚本；
- 最终验收报告。

### 4.2 本轮禁止完成

不得在本轮：

- 开发GridCrew正式业务功能；
- 创建大量React页面；
- 实现FastAPI业务接口；
- 实现Temporal Workflow或Activity；
- 实现LangGraph Agent；
- 实现数据库表和迁移；
- 接入Dify、FastGPT、MCP或运筹优化平台；
- 开发登录、聊天、任务、审批或员工管理功能；
- 创建临时任务状态机；
- 使用Mock冒充产品完成；
- 改写PRD、开发计划或高保真原型的产品内容；
- 擅自改变R1、R2、R3版本边界；
- 擅自更换Temporal-first架构；
- 提前执行M0任务书。

除文档治理、Git基线和小型校验脚本外，本轮不应产生正式应用代码。

---

## 5. 目标目录结构

整理完成后，项目根目录建议形成如下结构。可根据实际文件名做轻微调整，但不得改变总体边界：

```text
GridCrew/
├─ AGENTS.md
├─ README.md
├─ PROJECT_STATUS.md
├─ .gitignore
├─ .gitattributes
├─ .editorconfig
├─ .env.example
│
├─ docs/
│  ├─ index.md
│  │
│  ├─ product/
│  │  ├─ index.md
│  │  ├─ 02_GridCrew_终局架构与产品版本路线PRD_V2.2.docx
│  │  ├─ 03_GridCrew_终局架构与分版本完整开发计划_V2.2.docx
│  │  ├─ 04_GridCrew_Codex开发任务书统一命名基线.md
│  │  └─ prototype/
│  │     └─ 01_GridCrew_高保真原型_V2.2/
│  │
│  ├─ architecture/
│  │  ├─ index.md
│  │  ├─ ARCHITECTURE_BASELINE.md
│  │  ├─ DOMAIN_MODEL.md
│  │  ├─ EVENT_CATALOG.md
│  │  ├─ SECURITY_BASELINE.md
│  │  ├─ GLOSSARY.md
│  │  ├─ OPEN_QUESTIONS.md
│  │  └─ adr/
│  │     ├─ index.md
│  │     ├─ ADR-000-template.md
│  │     ├─ ADR-001-temporal-system-of-execution.md
│  │     ├─ ADR-002-modular-monolith-and-independent-workers.md
│  │     ├─ ADR-003-model-gateway.md
│  │     ├─ ADR-004-tool-gateway.md
│  │     ├─ ADR-005-multitenancy-from-day-one.md
│  │     ├─ ADR-006-artifact-evidence-separation.md
│  │     ├─ ADR-007-unified-events-and-channel-adapters.md
│  │     ├─ ADR-008-versioned-platform-assets.md
│  │     ├─ ADR-009-agent-runtime-boundary.md
│  │     └─ ADR-010-external-ai-platforms-as-skill-providers.md
│  │
│  ├─ tasks/
│  │  ├─ index.md
│  │  ├─ GridCrew_R1开发任务总纲.md
│  │  └─ GridCrew_M0_终局架构冻结与工程骨架任务书.md
│  │
│  └─ baseline/
│     ├─ index.md
│     ├─ SOURCE_MANIFEST.md
│     ├─ REQUIREMENTS_TRACEABILITY.md
│     └─ requirements_traceability.csv
│
└─ scripts/
   ├─ README.md
   └─ verify_project_baseline.py
```

### 5.1 目录整理规则

- 保留源资料原始内容，不得重新保存Word文档；
- 移动源文件前后记录SHA-256；
- 原型目录整体移动，不得破坏相对路径；
- 不得创建重复副本造成“哪个版本权威”不明确；
- 所有索引必须使用相对路径；
- Windows和Linux下路径都应可识别；
- 文件和目录尽量使用ASCII英文或现有稳定中文名，不再随意改名；
- 产品名统一为`GridCrew`；
- “电力行业数字员工平台”可作为中文副标题；
- 代码级标识统一采用`gridcrew`，但本轮不创建正式代码包。

---

## 6. Git基线要求

### 6.1 已存在Git仓库

如当前已经是Git仓库：

- 不得重新初始化；
- 不得改写提交历史；
- 不得执行强制重置；
- 不得删除用户已有分支；
- 先报告当前分支、提交和工作区状态；
- 在现有仓库中完成本任务。

### 6.2 尚未存在Git仓库

如当前不是Git仓库：

1. 执行`git init`；
2. 创建合理的`.gitignore`、`.gitattributes`和`.editorconfig`；
3. 完成本任务全部内容和验证后再创建基线提交；
4. 推荐提交信息：

```text
chore: establish GridCrew pre-development baseline
```

如果Git用户身份未配置：

- 不得伪造姓名或邮箱；
- 完成文件生成和验证；
- 报告需要用户执行的配置命令；
- 保持文件未提交状态。

### 6.3 Git安全限制

禁止：

- `git reset --hard`
- `git clean -fd`
- 强制推送
- 删除远程分支
- 修改用户全局Git配置
- 自动配置虚假Git身份

---

## 7. 根目录`AGENTS.md`要求

创建根目录`AGENTS.md`。该文件必须简洁、稳定、长期有效，不得把整份PRD复制进去。

至少包含以下内容。

### 7.1 产品定位

```text
GridCrew是面向电力行业的数字员工协作、装配、运行与治理平台。
它不是单一聊天机器人，不是运筹优化平台前端，也不绑定某个模型、
Dify、FastGPT、LangGraph或任何单一专业系统。
```

### 7.2 权威资料读取顺序

Codex执行任何任务前必须依次阅读：

1. 根目录`AGENTS.md`；
2. `docs/index.md`；
3. 与任务相关目录的`index.md`；
4. 当前里程碑任务书；
5. 架构基线和相关ADR；
6. 必要时查阅PRD、开发计划和原型。

### 7.3 不可变架构原则

必须明确：

- Temporal是正式任务、审批、定时任务、长任务、跨系统执行和补偿的唯一可靠执行内核；
- PostgreSQL保存业务事实和查询投影，不得成为第二套工作流执行引擎；
- LangGraph/Agent Runtime负责理解、规划、路由和智能判断，不得成为企业任务生命周期权威；
- 所有模型调用必须经过Model Gateway；
- 所有外部工具和系统调用必须经过Tool Gateway；
- Skill、Workflow、Tool、Connector、Digital Employee均为独立、版本化领域对象；
- Dify、FastGPT等只能作为Skill或能力提供者接入，不得成为GridCrew任务、权限或员工身份的权威中心；
- 运筹优化只是专业能力组件之一，禁止在平台核心中形成专用耦合；
- 所有核心对象从第一天考虑`tenant_id`、组织、空间和数据范围；
- Artifact与Evidence必须分离；
- 所有高风险操作必须由服务端权限和审批规则控制；
- 统一事件协议和Channel Adapter从首期成立；
- 后续版本只能扩展模块和能力，不能形成第二套并行内核。

### 7.4 Codex工作规则

至少明确：

- 修改前先读相关文档和现有代码；
- 不得越过当前任务边界；
- 不得用静态页面、Mock数据或LLM文本冒充真实完成；
- 不得未经批准改变架构基线；
- 重要架构变化必须新增ADR；
- 外部依赖和版本必须有理由并锁定；
- 所有实现必须配套测试；
- 失败时必须报告真实原因，不得隐藏；
- 每轮结束必须输出修改文件、验证结果、遗留问题和下一步；
- 不得提交密钥、密码、Token或客户真实敏感数据。

### 7.5 文档冲突优先级

建议固定为：

```text
用户当前明确指令
> 已批准的当前里程碑任务书
> AGENTS.md
> 已接受ADR与ARCHITECTURE_BASELINE
> PRD V2.2
> 开发计划V2.2
> 高保真原型
> 其他说明材料
```

如发生冲突，停止并报告，不得自行选择最方便的方案。

---

## 8. 架构基线文档要求

### 8.1 `ARCHITECTURE_BASELINE.md`

建立可供Codex快速读取的终局架构摘要，至少包含：

- 产品逻辑架构；
- Workspace、Studio、Runtime、Skills、Open Platform边界；
- Temporal和Agent双引擎职责；
- 核心服务边界；
- 数据与存储边界；
- 统一Gateway；
- 多租户；
- 权限和审批；
- Artifact与Evidence；
- 可观测性；
- 版本化；
- R1、R2、R3关系；
- 永久禁止的架构反模式；
- M0需冻结但尚待确认的技术决策。

不要凭空添加PRD未批准的业务功能。

### 8.2 `DOMAIN_MODEL.md`

定义但暂不实现以下一级领域对象：

- Tenant
- Organization
- Human User
- Service Identity
- Digital Employee
- Role
- Workspace
- Channel
- Message
- Task
- Workflow Definition
- Workflow Execution Reference
- Agent Run
- Skill
- Skill Version
- Skill Run
- Tool
- Tool Version
- Tool Call
- Connector
- Approval
- Human Input Request
- Human Takeover
- Artifact
- Evidence
- Audit Event
- Knowledge Source
- Memory Entry
- Model Policy
- Permission Policy
- Evaluation Suite
- Employee Release

每个对象至少说明：

- 定义；
- 主要职责；
- 关键标识；
- 所属租户范围；
- 与其他对象关系；
- 权威数据来源；
- 是否需要版本化；
- R1是否启用。

不得在M-1阶段生成ORM模型。

### 8.3 `EVENT_CATALOG.md`

建立初始统一事件目录，至少包含：

- `message.received`
- `agent.mentioned`
- `task.requested`
- `task.created`
- `task.assigned`
- `task.waiting_input`
- `task.progressed`
- `approval.requested`
- `approval.completed`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `task.failed`
- `task.completed`
- `artifact.published`
- `human.takeover_requested`
- `human.takeover_completed`

每个事件说明：

- 触发条件；
- 生产者；
- 消费者；
- 最小载荷；
- 关联ID；
- 幂等键；
- 租户字段；
- 是否属于审计事件。

当前只定义契约，不实现消息总线。

### 8.4 `SECURITY_BASELINE.md`

至少包含：

- 多租户隔离原则；
- 人类用户、数字员工、服务账号和外部系统身份；
- RBAC+ABAC边界；
- 最小权限原则；
- 高风险工具审批；
- 密钥和凭证不得进入仓库；
- Prompt Injection和工具注入风险；
- 外部Connector输入输出验证；
- 审计和证据保留；
- 数据脱敏；
- 日志不得泄露敏感内容；
- 非生产环境测试数据要求；
- 禁止数字员工直接进入生产控制闭环。

### 8.5 `GLOSSARY.md`

中英文统一定义至少包括：

- GridCrew
- Digital Employee
- Agent
- Agent Runtime
- Role
- Skill
- Tool
- Connector
- Workflow
- Temporal Workflow
- Task
- Agent Run
- Skill Run
- Tool Call
- Workspace
- Channel
- Artifact
- Evidence
- Approval
- Human Input
- Human Takeover
- Model Gateway
- Tool Gateway
- Channel Adapter
- R1/R2/R3
- Milestone
- Sprint

### 8.6 `OPEN_QUESTIONS.md`

仅记录从现有资料中无法确认但M0前或M0中必须决策的问题，例如：

- Node.js、Python、Temporal SDK等精确版本；
- 前端组件库最终选择；
- Python依赖管理方式；
- Monorepo工具；
- 身份提供者；
- 本地开发是否使用WSL2；
- CI平台；
-许可证策略；
- R1首批真实Skill和Connector；
- 是否使用Dify作为R1能力开发平台。

不得擅自将未确认问题写成既定事实。

---

## 9. 初始ADR要求

ADR采用统一模板，状态至少支持：

- Proposed
- Accepted
- Superseded
- Rejected

每份ADR至少包含：

- 标题；
- 状态；
- 日期；
- 背景；
- 决策；
- 理由；
- 影响；
- 替代方案；
- 后续约束；
- 关联PRD或任务。

必须创建以下初始ADR，并根据当前已批准设计将状态设为`Accepted`或`Proposed`：

1. Temporal作为唯一正式执行内核；
2. 模块化单体加独立Worker的首期部署形态；
3. 所有模型调用经过Model Gateway；
4. 所有外部调用经过Tool Gateway；
5. 多租户从第一天进入领域模型；
6. Artifact与Evidence分离；
7. 统一事件协议与Channel Adapter；
8. 平台资产全面版本化；
9. Agent Runtime与Temporal职责边界；
10. Dify/FastGPT作为Skill提供者而非平台内核。

对资料未明确批准的细节，不得擅自设置为Accepted。

---

## 10. 源资料清单要求

创建`docs/baseline/SOURCE_MANIFEST.md`，记录：

- 文件名；
- 相对路径；
- 文件类型；
- 版本；
- 文件大小；
- SHA-256；
- 是否为权威源；
- 用途；
- 是否允许修改。

源Word文件和原型业务内容默认：

```text
权威源：是
允许在本任务中修改：否
```

移动前后校验值必须一致。若不一致，立即停止并报告。

---

## 11. 需求追踪矩阵要求

同时创建：

- `REQUIREMENTS_TRACEABILITY.md`
- `requirements_traceability.csv`

至少包含字段：

```text
requirement_id
requirement_name
prd_section
prototype_page
release
priority
milestone
domain_object
workflow_or_service
api_or_event
test_type
acceptance_criteria
implementation_status
verification_evidence
notes
```

本轮只建立R1核心需求的初始条目，不需要穷举所有细节，但至少覆盖：

- 数字员工创建、测试、发布和入职；
- 协作空间与频道；
- 群聊中@数字员工；
- 正式任务创建；
- Temporal任务执行；
- 参数补充；
- 审批；
- 人工接管；
- Skill调用；
- Tool Gateway；
- Model Gateway；
- Artifact；
- Evidence；
- 审计；
- 多租户；
- RBAC+ABAC；
- 可观测性；
- 真实E2E；
- 故障恢复。

每个条目必须具有唯一ID，例如：

```text
GC-R1-EMP-001
GC-R1-TASK-001
GC-R1-WF-001
GC-R1-APPROVAL-001
GC-R1-SEC-001
```

---

## 12. GridCrew R1开发任务总纲要求

创建：

```text
docs/tasks/GridCrew_R1开发任务总纲.md
```

该文档不是单次执行任务，必须作为R1总地图。

至少包含：

### 12.1 R1目标

打通数字员工：

```text
创建
→ 测试
→ 发布
→ 入职
→ 进入协作空间
→ 接收正式任务
→ 调用Skill/Tool
→ 请求补参
→ 过程汇报
→ 提交成果
→ 人工审批
→ 异常恢复或接管
→ 归档证据
→ 绩效评测
```

### 12.2 R1不可简化底座

- Temporal；
- Agent Runtime；
- Model Gateway；
- Skill Registry；
- Tool Gateway；
- Connector Registry；
- 多租户领域模型；
- 权限与审批；
- Artifact与Evidence；
- 审计；
- OpenTelemetry；
- 资产版本化；
- Channel Adapter。

### 12.3 M0—M7里程碑

建议至少划分：

- M0：终局架构冻结与工程骨架；
- M1：核心领域模型、身份与基础数据；
- M2：Temporal可靠执行内核；
- M3：Agent Runtime、Model Gateway和Skill体系；
- M4：Workspace协作与正式任务闭环；
- M5：首批数字员工、Skill和Connector；
- M6：权限、安全、证据、评测与可观测性；
- M7：真实E2E、故障演练、试点准备和连续运行。

每个里程碑必须描述：

- 目标；
- 前置条件；
- 范围；
- 交付物；
- 不包含内容；
- 测试；
- 架构门禁；
- 完成定义；
- 下一阶段进入条件。

### 12.4 R1全局验收

至少包括：

- 真实Temporal执行；
- 系统重启后任务可恢复；
- 人工补参和审批可跨长时间等待；
- 外部调用具有幂等和审计；
- 没有第二套任务内核；
- 没有绕过Gateway；
- 至少2—3名数字员工；
- 至少2个真实Skill；
- 至少1个真实外部Connector；
- 至少1条多员工或复核流程；
- 至少1条人工接管流程；
- Mock E2E和Real E2E分离；
- 安全与租户隔离测试；
- 连续试运行门槛；
- 试点上线条件。

---

## 13. GridCrew M0任务书要求

创建：

```text
docs/tasks/GridCrew_M0_终局架构冻结与工程骨架任务书.md
```

M0任务书必须足够详细，可在下一轮直接交给Codex执行。

至少包含：

### 13.1 M0目标

建立最终可演进的工程骨架，不开发大规模业务功能。

### 13.2 M0建议范围

- 技术版本冻结；
- Monorepo骨架；
- React/Vite前端骨架；
- FastAPI后端骨架；
- Temporal Server与Worker骨架；
- Agent Worker与Tool Worker边界；
- PostgreSQL；
- MinIO；
- OpenTelemetry Collector；
- Docker Compose本地环境；
- 配置和密钥管理；
- 日志规范；
- 健康检查；
- 数据迁移框架；
- 共享Contracts包；
- CI；
- 代码格式化、Lint、类型检查和测试；
- 架构依赖约束；
- 最小真实Temporal健康工作流；
- Windows/WSL2开发说明；
- 工程启动与停止脚本；
- README和开发者手册。

### 13.3 M0禁止范围

- 不开发完整聊天系统；
- 不开发正式员工业务页面；
- 不实现完整Agent能力；
- 不实现业务Skill；
- 不接客户系统；
- 不用数据库任务表代替Temporal；
- 不生成大量假数据页面；
- 不实现R2/R3功能。

### 13.4 M0验收门禁

至少包括：

- 一条命令或清晰步骤启动本地依赖；
- Web/API/Worker健康检查通过；
- Temporal Web可访问；
- 最小Workflow与Activity真实执行；
- 任务失败和重试可观察；
- PostgreSQL迁移可执行和回滚；
- OpenTelemetry至少贯穿API与Worker；
- 无密钥进入仓库；
- 格式化、Lint、类型检查、单测和架构测试全部通过；
- CI执行同样门禁；
- Windows路径和Docker挂载验证；
- 工程骨架与最终架构一致；
- 不存在第二套任务执行逻辑。

### 13.5 M0结束后必须停止

M0任务书必须明确要求：

- 完成M0后停止；
- 输出完整结果；
- 不自动进入M1；
- 等待独立验收和整改。

---

## 14. 根目录基础文件要求

### 14.1 `README.md`

内容至少包含：

- GridCrew简介；
- 当前阶段为M-1完成、M0待执行；
- 权威文档入口；
- 目录结构；
- 如何阅读项目；
- 如何验证项目基线；
- 下一步；
- 当前没有正式应用代码的说明。

不得宣称产品已经可运行。

### 14.2 `PROJECT_STATUS.md`

记录：

- 当前Release：R1；
- 当前里程碑：M-1；
- M-1状态；
- M0状态；
- 已冻结决策；
- 待确认问题；
- 最近一次基线更新时间；
- 下一门禁。

### 14.3 `.gitignore`

至少考虑：

- Python；
- Node.js；
- IDE；
- 操作系统临时文件；
- `.env`；
- 密钥；
- 构建产物；
- 测试缓存；
- Docker本地数据；
- 日志；
- 临时Office文件。

不得忽略权威文档、任务书、ADR和需求矩阵。

### 14.4 `.gitattributes`

至少：

- 统一文本换行策略；
- Markdown、Python、TypeScript、YAML等文本文件；
- DOCX、PNG、ZIP等二进制文件；
- 避免Office文件被错误文本合并。

### 14.5 `.editorconfig`

至少规定：

- UTF-8；
- LF；
- 末尾换行；
- 去除多余空格；
- Markdown合理例外；
- Python和前端默认缩进。

### 14.6 `.env.example`

本轮只建立未来配置命名示例，不包含真实密钥，例如：

```text
GRIDCREW_ENV=
GRIDCREW_DATABASE_URL=
GRIDCREW_TEMPORAL_ADDRESS=
GRIDCREW_TEMPORAL_NAMESPACE=
GRIDCREW_MINIO_ENDPOINT=
GRIDCREW_OTEL_EXPORTER_ENDPOINT=
```

不得把具体技术选型未确认的变量写成正式承诺。

---

## 15. 基线验证脚本

创建：

```text
scripts/verify_project_baseline.py
```

脚本仅使用Python标准库，至少检查：

- 必需文件是否存在；
- 必需目录是否存在；
- 根目录是否存在`AGENTS.md`；
- 源资料清单中的文件是否存在；
- 源资料SHA-256是否匹配；
- Markdown文档中主要相对链接是否有效；
- 是否误提交`.env`、密钥常见文件或临时Office文件；
- 产品名是否统一为GridCrew；
- R1总纲和M0任务书是否存在；
- 初始ADR数量是否达标；
- 需求追踪CSV字段是否完整。

执行方式：

```bash
python scripts/verify_project_baseline.py
```

Windows环境同样应可运行。

脚本只做检查，不自动删除或修改用户文件。

---

## 16. 文档质量要求

所有新建Markdown文档必须：

- 使用UTF-8；
- 标题层级清晰；
- 使用相对链接；
- 不复制粘贴大量重复内容；
- 明确来源和版本；
- 区分“已批准”“建议”“待确认”；
- 不将推测写成事实；
- 不宣称未开发能力已经完成；
- 不出现旧产品名替代GridCrew；
- 不将运筹优化描述为平台唯一核心；
- 不将Dify或FastGPT描述为平台任务内核；
- 不混淆Release、Milestone和Sprint。

---

## 17. 验证要求

完成后必须执行并记录：

1. `python scripts/verify_project_baseline.py`
2. Git状态检查；
3. 源文件SHA-256前后对比；
4. Markdown主要链接检查；
5. 全局搜索：
   - 是否错误出现第二套任务内核表述；
   - 是否错误将LangGraph设为业务任务权威；
   - 是否错误将Dify设为平台内核；
   - 是否错误把运筹优化设为唯一能力；
   - 是否将“第一阶段”与M1混用；
6. 文件树核对；
7. 如已创建提交，展示提交哈希和提交内容摘要。

不得仅凭“文件已生成”宣布通过。

---

## 18. 完成标准

只有满足以下条件，本任务才可标记为完成：

- 项目资料已规范归档；
- 源资料内容未被改变；
- SHA-256记录完整；
- Git状态清晰；
- 根目录`AGENTS.md`可长期使用；
- 架构基线与PRD一致；
- 初始ADR已建立；
- 术语表已建立；
- 需求追踪矩阵已建立；
- R1总纲足够控制M0—M7；
- M0任务书可直接执行；
- 验证脚本通过；
- 没有提前开发M0或业务功能；
- 没有未说明的架构决策；
- 没有把待确认事项写成已冻结事项；
- 最终报告真实、完整、可复核。

---

## 19. 异常与停止条件

遇到以下情况必须停止，不得自行处理：

- 源Word文件或原型损坏；
- 移动前后SHA-256不一致；
- 已存在未说明的业务代码；
- 已存在Git历史且与任务要求冲突；
- PRD和开发计划对同一核心架构有实质冲突；
- 现有文件名或版本无法确认；
- 无法安全移动原型目录；
- 需要删除用户文件；
- 需要修改源文档内容；
- 需要替用户决定重大技术路线；
- Git操作可能覆盖现有历史。

停止时应说明：

- 发现了什么；
- 影响哪些步骤；
- 已完成哪些安全操作；
- 需要用户做什么决定。

---

## 20. 最终汇报格式

完成后严格按以下格式汇报：

### 20.1 总体结论

- M-1是否完成；
- 是否具备进入M0条件；
- 是否存在阻断项。

### 20.2 实际执行内容

逐项说明：

- 目录整理；
- Git基线；
- AGENTS.md；
- 架构基线；
- ADR；
- 术语表；
- 需求追踪；
- R1总纲；
- M0任务书；
- 验证脚本。

### 20.3 新增、移动和修改文件

分类列出：

- 新增；
- 移动；
- 修改；
- 未改动的权威源。

### 20.4 验证结果

给出：

- 验证命令；
- 通过/失败；
- 关键输出；
- SHA-256核对结果；
- Git状态。

### 20.5 已冻结架构决策

只列已从现有资料确认的决策。

### 20.6 待用户确认问题

列出所有未决问题，不得隐藏。

### 20.7 风险与建议

说明进入M0前仍需关注的风险。

### 20.8 下一步

仅说明：

> 可进入GridCrew M0任务书的独立执行与验收。

不得在本轮自动开始M0。

---

## 21. 执行指令

现在开始执行本任务。

先完成“开工前强制要求”并向我展示：

1. 当前文件树；
2. Git状态；
3. 已读取资料；
4. 你理解的GridCrew产品与架构约束；
5. 执行计划。

随后再实施文件整理和文档建设。

不得跳过检查直接批量修改。
