# NEXWEAVE｜完整分阶段开发任务总纲 V1.0

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 文档性质：Codex 分阶段开发总纲与质量门禁基线  
> 上位资料：NEXWEAVE PRD V1.0、高保真原型 V1.0、M-1 治理基线、GridCrew 架构与治理参考  
> 执行方式：一个 Milestone 一次下发、一次验收；未通过不得进入下一阶段

---

## 1. 总体目标

NEXWEAVE 要建立企业知识从原始资料到正式知识服务的标准生产线：

```text
资料导入 → 文档解析 → Schema约束 → LLM知识编译
→ Evidence绑定 → 专家审核 → 质量评估 → 不可变Release
→ 查询/API/业务应用调用 → 反馈与增量更新
```

完整开发必须同时实现：

1. **可信性**：正式知识有来源、证据、审核、版本和责任记录；
2. **通用性**：平台核心与领域包解耦，不为RCA或单一客户写专用内核；
3. **可靠性**：长任务、人工审核、发布和跨系统回流可恢复、可重试、可审计；
4. **可产品化**：支持私有化、企业治理、领域包、SDK、GridCrew及其他应用接入；
5. **可演进性**：R1、R2、R3共享同一核心对象、版本和Release语义，不建立平行内核。

---

## 2. 产品版本与Milestone

| 阶段 | 名称 | 产品版本 | 建议周期 |
|---|---|---|---|
| M-1 | 编码前启动准备与治理基线 | 开发准备 | 1—2周 |
| M0 | 终局架构冻结与工程骨架 | R1：可信知识闭环与联合试点版 | 2—3周 |
| M1 | 平台基础、身份权限与核心领域模型 | R1：可信知识闭环与联合试点版 | 4周 |
| M2 | Temporal可靠知识工作流内核 | R1：可信知识闭环与联合试点版 | 3周 |
| M3 | 资料中心、版本管理与文档解析 | R1：可信知识闭环与联合试点版 | 4—5周 |
| M4 | Schema Studio与Domain Pack运行时 | R1：可信知识闭环与联合试点版 | 4—5周 |
| M5 | LLM知识编译核心与Wiki工作台 | R1：可信知识闭环与联合试点版 | 6周 |
| M6 | 主张证据、冲突处理与专家审核闭环 | R1：可信知识闭环与联合试点版 | 4—5周 |
| M7 | 知识质量、不可变发布、图谱检索与可信问答 | R1：可信知识闭环与联合试点版 | 5—6周 |
| M8 | 连接器生态、Obsidian适配与GridCrew首期集成 | R1：可信知识闭环与联合试点版 | 4—5周 |
| M9 | Equipment RCA领域包、纵向闭环与联合试点验收 | R1：可信知识闭环与联合试点版 | 5—6周 |
| M10 | 企业级治理、多空间运营与精细权限 | R2：企业产品化与规模部署版 | 4—5周 |
| M11 | 高级检索、知识图智能与持续评估 | R2：企业产品化与规模部署版 | 5—6周 |
| M12 | 高可用、灾备、国产化与规模性能 | R2：企业产品化与规模部署版 | 5—6周 |
| M13 | 私有Domain Pack生态与供应链治理 | R3：领域生态与规模运营版 | 4—5周 |
| M14 | 多应用知识服务与GridCrew深度闭环 | R3：领域生态与规模运营版 | 5—6周 |
| M15 | 商业发布、规模试点与运营移交 | R3：领域生态与规模运营版 | 4—6周 |

### 2.1 Release划分

- **R1（M0—M9）**：完成可信知识闭环、GridCrew只读接入和Equipment RCA联合试点；
- **R2（M10—M12）**：完成企业治理、高级检索、规模性能、灾备和国产化；
- **R3（M13—M15）**：完成Domain Pack生态、多应用闭环和商业发布运营。

周期为标准团队估算，可以并行前端、后端、AI和测试工作，但不得打乱阶段依赖和质量门禁。

---

## 3. 全局不可变原则

1. Raw First：原始资料及其版本、哈希、来源和密级是事实基线，LLM 不得覆盖原文。
2. Schema Before Generation：未绑定有效 SchemaVersion 的知识编译不得进入正式流水线。
3. Evidence Native：正式 Claim 与因果 Relation 必须绑定可定位 Evidence。
4. Human in the Loop：高风险知识、冲突处理和 Release 必须经过人工审核与批准。
5. Draft / Release Separation：草稿、审核中对象和正式 Release 必须逻辑隔离，业务应用默认只读 Release。
6. Conflict Instead of Overwrite：新资料与既有知识不一致时生成 Conflict，不静默覆盖。
7. Version Reproducibility：回答、审核、评估和发布均可还原 Source、Schema、Prompt、Model 与 Release 版本。
8. Platform / Domain Decoupling：平台核心不得写死 RCA、核电、泵、轴承等领域概念。
9. Gateway First：模型、解析器、搜索、对象存储和外部系统均通过 Gateway/Provider/Connector 接口接入。
10. Reliable Workflow：长任务、人工审核、发布和跨系统回流必须由 Temporal 等可靠工作流承载。
11. Audit by Default：关键读写、模型调用、审核、导出、发布、回滚与权限变更必须审计。
12. GridCrew Boundary：NEXWEAVE 独立部署，GridCrew 通过版本化 API、事件与 SDK 消费知识。

---

## 4. 全局领域与状态权威

### 4.1 核心对象

Tenant、Organization、User、ServiceIdentity、KnowledgeSpace、SourceDocument、SourceVersion、ParseJob、SchemaDefinition、SchemaVersion、EntityType、RelationType、PageTemplate、WikiPage、WikiPageVersion、Entity、EntityAlias、Relation、Claim、Evidence、Conflict、CompileJob、CompileStep、ReviewTask、ReviewAction、Approval、EvaluationSuite、EvaluationRun、Release、ReleaseItem、DomainPack、DomainPackVersion、Installation、Connector、ModelProfile、PromptVersion、QuerySession、QueryAnswer、Citation、AuditLog。

### 4.2 权威状态

- 原始文件字节：对象存储 + SourceVersion checksum；
- 业务对象和审核/发布结果：关系数据库；
- 长流程执行：Temporal Workflow；数据库仅保存查询投影；
- Markdown/YAML：交换、展示和导出表示，不是生产业务状态唯一来源；
- 搜索、向量和图数据库：Release可重建查询投影，不是正式知识权威源；
- 正式业务调用：固定Release及其索引版本。

---

## 5. 工程交付策略

1. **架构先行**：M0冻结领域、状态、版本、API、事件、Workflow、权限与Pack契约；
2. **纵向闭环**：每个阶段必须交付真实前后端或真实工作流增量，避免横向铺满静态页面；
3. **契约优先**：前端、API、Worker、Provider、Connector、Pack和GridCrew集成先定义Schema；
4. **真实执行**：Mock用于单元和开发，阶段验收必须使用真实数据库、对象存储和Temporal；
5. **治理内建**：租户、权限、证据、审计、版本、评测和可观测性从R1存在；
6. **模块化单体优先**：逻辑边界固定，首期控制物理服务数量；规模增长再按接口拆分；
7. **迁移零债务**：后续版本只能扩展对象和Provider，不推倒R1核心表与Release语义。

---

## 6. 每阶段统一质量门禁

### 6.1 代码门禁

- format、lint、typecheck、unit test、contract test、migration test、frontend build全部通过；
- 禁止新增高危漏洞、明文密钥和未说明的强传染性许可证；
- 核心代码需包含类型、错误处理、审计和自动化测试；
- 关键对象/状态/API/事件变更必须有ADR和迁移方案。

### 6.2 架构门禁

- domain/contracts不得依赖Web框架、数据库、Temporal或模型厂商SDK；
- Workflow保持确定性，外部操作只能在Activity；
- Domain Pack不得依赖平台内部实现；
- Connector不得绕过Source、权限、审计与幂等；
- Search/Vector/Graph不得成为不可重建权威源；
- GridCrew集成不得侵入NEXWEAVE核心。

### 6.3 知识质量门禁

- 正式Claim和因果Relation均有Evidence；
- Evidence可定位到SourceVersion原文；
- 未关闭阻断冲突不能发布；
- Release包含固定Schema和索引配置；
- 查询结果记录Release和Citation；
- 证据不足时必须明确不确定，不得生成伪引用。

### 6.4 阶段停止门禁

Codex完成当前任务后只输出执行回报，不得：

- 自行开始下一阶段；
- 自动生成或修改下一阶段正式任务书；
- 自动push、创建远程仓库或伪造Git身份；
- 用“后续再补”掩盖P0架构、权限、证据或版本缺口。

---

## 7. 全局测试体系

- 单元测试：领域规则、状态机、权限、幂等、转换和Provider；
- 契约测试：OpenAPI、事件、SDK、Pack manifest和GridCrew接口；
- 集成测试：PostgreSQL、MinIO、Temporal、Redis、模型/解析Provider；
- Workflow测试：重放、时间跳跃、取消、超时、重试、补偿和Worker恢复；
- E2E：Source→Compile→Review→Evaluate→Release→Query；
- 安全测试：越权、Prompt注入、恶意文档、凭据泄露、导出和下载；
- 性能测试：页面、检索、任务更新、编译吞吐和百万级数据；
- 恢复测试：数据库、对象存储、Temporal、Release和索引重建；
- 领域评测：可回答、不可回答、冲突、反事实、多来源和证据不足问题。

---

## 8. 推荐仓库中的任务书位置

```text
docs/development/tasks/
├── 00_NEXWEAVE_完整分阶段开发任务总纲_V1.0.md
├── 01_NEXWEAVE_M-1_编码前启动准备与治理基线建立任务书.md
├── 02_NEXWEAVE_M0_终局架构冻结与工程骨架任务书.md
├── ...
└── 17_NEXWEAVE_M15_商业发布规模试点与运营移交任务书.md
```

任务书是上位执行约束，Codex不得在执行中自行改写任务目标；发现冲突时写入OPEN_QUESTIONS或执行回报。

---

## 9. 完整验收节点

### R1验收（M9后）

- 资料到正式Release全链路真实可用；
- 16个一级模块完成MVP所需功能；
- GridCrew可绑定固定知识Release；
- Equipment RCA Pack证明平台与领域解耦；
- 来源可追溯率与Schema合规率100%；
- 完成真实E2E、故障演练和专家试点。

### R2验收（M12后）

- 企业多租户、精细权限、配额和运营治理可用；
- 高级检索/图谱Provider可替换且不改变权威语义；
- 高可用、灾备、性能、离线与国产化适配通过；
- 完成R2生产部署和运维交付。

### R3验收（M15后）

- Domain Pack具备企业级开发、签名、分发、升级和回滚能力；
- GridCrew双向知识闭环和多应用服务可用；
- 至少两个领域/应用规模试点证明通用性；
- 产品、运营、SLA、支持和商业发布体系完整。

---

## 10. 执行说明

建议先执行现有M-1；每次仅向Codex下发一个Milestone文件。阶段完成后将：

1. Codex完整执行回报；
2. 最新项目工程或Git diff；
3. 测试结果与未决问题；

交回产品/架构负责人验收，再决定是否下发下一阶段。后续任务书可以根据真实执行结果做小范围修订，但不得改变本总纲的产品边界与不可变原则。
