# GridCrew 架构基线

来源：PRD V2.2、完整开发计划 V2.2、高保真原型 V2.2、Codex 统一命名基线。

## 已批准的产品逻辑架构

GridCrew 是电力行业数字员工平台，产品域包括：

- GridCrew Workspace：人机协作、群聊、任务、审批和成果工作台。
- GridCrew Studio：数字员工创建、岗位、Skill、知识、权限、评测与发布中心。
- GridCrew Runtime：Temporal 可靠执行、Agent Runtime、网关、证据与可观测性底座。
- GridCrew Skills：Skill、Tool、Connector 治理体系。
- GridCrew Open Platform：R3 阶段 API、SDK、能力市场与生态伙伴体系。

## Temporal 与 Agent 双引擎职责

- Temporal：正式任务、审批、定时任务、长任务、跨系统执行、失败重试、补偿、人工等待和恢复的唯一可靠执行内核。
- Agent Runtime/LangGraph：理解、规划、路由、补参判断、解释和智能决策，不拥有企业任务生命周期权威。
- PostgreSQL：保存业务事实、配置、权限、版本和查询投影，不作为第二套工作流执行引擎。

## 核心服务边界

- Identity/IAM：人类用户、数字员工、服务身份、外部系统身份。
- Workspace/Channel：协作空间、频道、消息、任务入口。
- Task/Workflow：任务定义、任务实例、Temporal 执行引用。
- Agent Runtime：Agent Run、计划、推理和路由。
- Skill Registry：Skill、Skill Version、Skill Run。
- Tool Gateway：Tool、Tool Version、Tool Call、Connector 调用治理。
- Model Gateway：模型策略、模型调用、供应商隔离。
- Artifact/Evidence：正式成果与证据链分离保存。
- Audit/Evaluation/Observability：审计、评测、指标、日志和追踪。

## 数据与存储边界

- PostgreSQL 保存权威业务事实、租户范围、权限、版本和查询投影。
- 对象存储保存大文件、Artifact、Evidence 原始文件和不可变快照。
- Temporal Event History 只保存工作流状态和必要引用，不保存大文件和长文本。
- 日志和追踪不得泄露密钥、Token、客户敏感数据或完整提示词中的敏感内容。

## 统一 Gateway

- 所有模型调用必须经过 Model Gateway。
- 所有外部工具和系统调用必须经过 Tool Gateway。
- Agent 不得直接访问客户系统。
- Gateway 必须处理租户隔离、权限、风险、审批、幂等、超时、重试、限流、脱敏、回执和审计。

## 多租户、权限和审批

所有核心对象从第一天包含 `tenant_id`，并考虑组织、空间和数据范围。权限采用 RBAC+ABAC，所有高风险操作由服务端权限和审批规则控制。

## Artifact 与 Evidence

Artifact 是正式交付成果，可版本化、归档、引用和复用。Evidence 是支持复现、审计和问题回放的证据，保存输入、输出、回执、审批、日志摘要和校验值。二者必须分离。

## 可观测性与版本化

R1 起需要覆盖 API、Worker、Temporal、Tool Call、Model Call、Skill Run 和 Artifact 发布链路。Digital Employee、Skill、Workflow、Tool、Connector、Model Policy、Artifact、Evaluation Suite 等均为版本化领域对象。

## R1、R2、R3 关系

R1、R2、R3 共享同一任务内核、领域模型、Gateway、权限治理和数据边界，差异只是启用能力范围。后续版本只能扩展模块和能力，不能形成第二套并行内核。

## 永久禁止的架构反模式

- 用数据库状态机、消息队列或 Agent 图替代 Temporal 执行内核。
- 领域代码直接绑定模型厂商 SDK。
- Agent 直接调用外部系统或客户系统。
- 将 Dify、FastGPT 或 LangGraph 设为平台任务、权限或员工身份权威中心。
- 将运筹优化耦合为平台唯一核心。
- 用聊天消息替代正式 Task、Artifact、Evidence 和 Audit。
- 用 Mock E2E 冒充真实验收。

## M0 正式任务书边界

M0 的技术版本、工程骨架、分轮要求、质量门禁和交付物已由用户提供的 [正式 M0 任务书](../tasks/GridCrew_M0_终局架构冻结与工程骨架正式任务书.md) 冻结。本架构基线不替代该文件，也不提前执行其中任何内容。

R1 首批真实 Skill、Connector、Dify 接入策略、记忆与向量检索实现及客户身份系统优先级仍见 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)，需要独立用户决策。
