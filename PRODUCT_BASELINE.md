# NEXWEAVE Product Baseline

> 状态：M-1 产品基线持续有效；M1—M8 已正式验收；用户于 2026-09-01 正式下发 M9。Equipment RCA Pack、9 份公开资料准入和 4 份代表性 Source→Compile 技术试点已按 ADR-0029/0030 完成；GridCrew 联合试点延期。M9 当前以 NEXWEAVE 独立公开资料技术试点为边界，专家、阈值和真实评审/Release 证据仍为 P0。
> 来源：PRD V1.0、高保真原型 V1.0、完整分阶段开发总纲 V1.0  
> Release 权威解释：用户已确认统一采用总纲，R1 = M0—M9

## 1. 一句话定位

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台，将原始资料转化为可阅读、可计算、可审核、可追溯、可版本化和可由业务系统调用的可信知识资产。

## 2. 产品不是

- 不是单纯文档管理系统；
- 不是只提供向量检索和问答的 RAG 知识库；
- 不是 Obsidian 企业版；
- 不是写死某个行业或设备类型的 RCA 系统；
- 不是替代专家作最终决策的黑盒；
- 不是 GridCrew 的内部模块、聊天或数字员工执行引擎。

## 3. 三层产品结构

```text
NEXWEAVE Standard Platform
  ├─ 通用知识生产、治理、发布与查询能力
  ├─ Domain Pack
  │    └─ 声明式 Schema、模板、术语、Prompt、规则、评测和样例
  └─ Business App
       └─ 通过固定 Release、API、事件或 SDK 消费可信知识
```

平台内核定义通用语义和治理规则；Domain Pack 定义领域语义；Business App 负责业务场景和最终业务动作。三层不得反向侵入。

### 3.1 语义模型定位

NEXWEAVE 在 Schema 与 Domain Pack 内提供轻量 Semantic Model：稳定类型身份、属性、类型层级、关系约束、术语和跨 Pack 映射。R1 不新增独立 Ontology 产品域或 `OntologyVersion`；不可变 `SchemaVersion` 是解析后有效语义模型的唯一版本权威。Schema 合规不替代 Claim/Relation 的 Evidence 与审核。

产品界面可在 Schema Studio 中提供“语义模型”视图，但不建设 RDF/OWL/SPARQL 编辑器、描述逻辑推理机或以图数据库为权威的完整本体平台。

## 4. 用户与责任

| 角色 | 主要责任 |
|---|---|
| 平台管理员 | 平台、身份、模型、存储、集成、安全和审计策略 |
| 空间管理员 | 空间、成员、Schema、审核与发布策略 |
| 知识工程师 | 资料、编译、消歧、冲突、草稿与初审 |
| 领域专家 | 专业复核、修改、驳回、不确定性和批准 |
| 普通业务用户 | 只读正式知识、可信查询和反馈 |
| 应用开发者 | 固定 Release 的 API/SDK/Webhook 集成 |
| 审计/质量人员 | 版本还原、审计和质量评估 |

## 5. 16 个一级功能域

| ID 前缀 | 功能域 | R1 最小目标 |
|---|---|---|
| `NXW-DASH` | 总览 | 当前空间的建设、质量、风险和待办指标 |
| `NXW-SPACE` | 知识空间 | 空间、成员、配置、密级和隔离 |
| `NXW-SOURCE` | 资料中心 | Raw 导入、版本、解析、预览和 SourceAnchor |
| `NXW-COMPILE` | 编译中心 | 可恢复、可追踪、可重放的知识编译任务 |
| `NXW-WIKI` | Wiki | 页面、结构化属性、版本、diff、人工保护区 |
| `NXW-SCHEMA` | Schema Studio | 语义模型、Schema/模板/规则配置、版本、Pack 组合和兼容检查 |
| `NXW-CLAIM` | 主张与证据 | Claim/Evidence、正反证据和原文定位 |
| `NXW-GRAPH` | 关系图谱 | 证据约束的 Relation 展示与遍历 |
| `NXW-CONFLICT` | 冲突中心 | 冲突发现、分派、处置和发布阻断 |
| `NXW-REVIEW` | 审核中心 | 初审、复核、批准、职责分离和审计 |
| `NXW-QUALITY` | 质量中心 | Lint、标准问题集、回归评测和门禁 |
| `NXW-RELEASE` | 发布管理 | 不可变 Release、审批、切换、回滚和订阅 |
| `NXW-QUERY` | Ask NEXWEAVE | 固定 Release、带 Citation、可拒答的可信查询 |
| `NXW-PACK` | 领域知识包 | 声明式 Pack 的安装、版本、兼容和回滚 |
| `NXW-INTEGRATION` | 集成中心 | Connector、SDK、Webhook、Obsidian、GridCrew |
| `NXW-ADMIN` | 系统管理 | 身份、权限、模型、Prompt、凭据、审计和健康 |

## 6. 核心业务闭环

```text
KnowledgeSpace → DomainPack/SchemaVersion → SourceVersion → Parse
→ Compile Candidate → Wiki/Entity/Relation/Claim/Evidence Draft
→ Conflict → Review/Approval → Evaluate → immutable Release
→ Query/API/GridCrew → Feedback → new Draft
```

AI 只生成候选知识。未经过 Evidence、审核、质量门禁和 Release 的内容不得成为正式知识。

Domain Pack 声明先经确定性组合形成不可变 SchemaVersion；CompileJob 和 Release 只引用该有效快照。编译中发现的新概念只能形成下一 SchemaVersion 的变更候选，不能修改当前发布模型。

## 7. MVP 必须完成的 14 项能力

1. 创建知识空间；
2. 上传 PDF、Word、Markdown；
3. 配置基础实体与关系 Schema；
4. LLM 自动创建或更新 Wiki 草稿；
5. 自动提取来源引用；
6. Wiki 编辑和差异展示；
7. 专家审核；
8. Claim/Evidence 查看；
9. 基础关系图；
10. 冲突识别；
11. Lint 检查；
12. 发布 Markdown/JSON 正式版本；
13. 基于正式版本的可信问答；
14. 安装 Equipment RCA 示例领域包。

R1 总纲原计划在 MVP 上增加可靠 Workflow、身份权限、审计、连接器、GridCrew 只读集成及真实 RCA 联合试点。用户于 2026-09-01 通过 ADR-0030 将 GridCrew 开发和联合试点延期；当前 R1/M9 只验收 NEXWEAVE 独立的公开资料 Equipment RCA 技术试点，不得将延期描述为已完成。

## 8. R1 暂不建设或不作正式验收

- 大规模实时数据流和全自动根因诊断；
- 自动执行纠正措施或替代最终工程判断；
- 复杂图算法和专用图数据库强依赖；
- 多租户公有 SaaS 商业运营；
- 全类型音视频解析；
- 第三方 Domain Pack 市场交易；
- 高可用、灾备、国产化认证和百万实体正式性能结论（R2）；
- 私有 Pack 供应链生态和多应用双向闭环（R3）。

## 9. NEXWEAVE 与 GridCrew 边界

| NEXWEAVE | GridCrew |
|---|---|
| 生产、审核、评估和发布可信知识 | 数字员工、任务协作、编排和执行 |
| Source、Schema、Wiki、Claim、Evidence、Release | Task、EmployeeRelease、Skill、Tool、Artifact、Evidence |
| 发布固定知识版本并提供查询/证据/图 API | Skill 绑定固定知识 Release 并在任务中消费 |
| 接受资料、反馈、案例草稿和冲突线索 | 不得直接修改 NEXWEAVE 正式知识 |

两边可兼容对象语义和事件 Envelope，但不共享数据库、运行状态或产品生命周期。共享/复用 IAM、Model Gateway 与 Evidence 契约仍需 ADR 批准。

## 10. Equipment RCA Pack 验证目标

首发 Pack 用于证明平台与领域解耦：设备、部件、现象、故障模式、原因、机理、验证、措施、案例等全部通过 Pack 声明提供。R1 试点验证相似案例、候选原因、支持/反对证据、验证建议和证据不足表达，不宣称实时诊断、概率预测或自动决策。

## 11. Release 基线统一说明

PRD V1.0 第 17 章中的“R1：产品化增强”属于早期路线命名。经用户确认，当前执行统一以完整开发总纲为权威：

- R1 = M0—M9；
- R2 = M10—M12；
- R3 = M13—M15；
- M0-Lite 是补充验证轨道，不是正式 Release。

该解释不改写原始 PRD，只消除后续需求追踪和验收歧义。

## R1 / M9.5 阶段 D 收口（2026-09-10）

现有 Wiki 运行态的绑定预检、条件预测比较、固定发布材料回接和原文追溯完成关键路径浏览器验证。Query/发布图谱按当前可见性提供冻结知识，页面明确区分派生预测与正式依据。该完成度仅表示合成开发环境的软件可用性；工业模型效果、阈值批准与设备适用性仍未验收，停止在 D，不进入 M10。
