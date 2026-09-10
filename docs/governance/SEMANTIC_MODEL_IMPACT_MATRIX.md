# Semantic Model Milestone Impact Matrix

> 状态：2026-08-29 由用户明确要求建立；ADR-0022 已冻结总影响。M4 已完成任务书治理校准，M5—M15 仅标记强制影响和更新触发器，仍须在各 Milestone 正式下发前依据已验收实况精确校准。

## 1. 使用规则

本矩阵防止两个相反风险：现在一次性把未经实现验证的细节写死到所有后续任务书，或后续 Milestone 忽略 ADR-0022 而重新发明语义版本。

状态定义：

| 标记 | 含义 |
|---|---|
| `CALIBRATED` | 任务书已完成本轮详细校准，但不表示已下发或实现 |
| `MANDATORY` | 正式下发该 Milestone 前必须更新任务书和相关基线 |
| `TARGETED` | 必须做影响审查；仅在触发条件成立时增加对象/API/验收范围 |
| `NO DIRECT CHANGE` | 当前无直接范围变化，但仍受全局不变量约束 |

每次校准必须以最近已正式验收的 Milestone 为输入，并更新：任务书状态、ADR 依赖、对象/API/Event/Workflow、迁移、权限、安全、测试、需求追踪和停止边界。不得根据本矩阵提前声称功能已实现。

## 2. 全局不变量

M4—M15 持续适用：

1. R1 有效语义模型的唯一版本权威是不可变 SchemaVersion；不得静默新增 OntologyVersion。
2. stable key、类型层级、术语和映射属于 SchemaVersion；Entity/Relation/Claim 是知识实例/事实，二者不得混表或混生命周期。
3. Schema 合规不等于事实正确，不替代 Evidence、审核、Conflict 和 Release。
4. Domain Pack 依赖必须解析为精确版本/checksum 并确定性组合；禁止安装顺序覆盖。
5. CompileJob 和 Release 必须固定 SchemaVersion/composition checksum；历史版本不可受后续 Pack 变化影响。
6. LLM 只提出下一 SchemaVersion 的候选，不得修改当前 PUBLISHED 模型或自动确认 EXACT mapping。
7. PostgreSQL/Release 是权威；RDF、图数据库、搜索、向量和 Agent Prompt 只能是导出、投影或消费表示。
8. 若出现独立本体生命周期、外部标准无损往返或逻辑推理需求，必须新 ADR，不得在 M11 图智能中顺带引入。

## 3. Milestone 影响总览

| Milestone | 状态 | 必须纳入的语义影响 | 本轮处理 |
|---|---|---|---|
| M4 | FORMALLY ACCEPTED | SchemaVersion 单一权威、stable key、类型/属性/层级/关系、术语/映射、Pack 确定性组合、兼容/迁移/安全 | 已完成校准、实施、独立审查、本地技术验收，并于 2026-08-30 由用户正式验收 |
| M5 | MANDATORY | Compile 锁定 PUBLISHED SchemaVersion/composition；类型约束抽取、歧义映射、SemanticChangeProposal、Entity 实例绑定 stable key | 下发 M5 前详细校准 |
| M6 | TARGETED | 区分语义不合规、事实冲突和证据不足；审核 EXACT mapping/高风险语义变更；Claim predicate 与 RelationType 对齐 | M5 验收后校准 |
| M7 | MANDATORY | Release 固化 composition/Pack inputs；Query/Graph 支持类型层级与显式 mapping；索引由固定语义快照重建 | M6 验收后详细校准 |
| M8 | TARGETED | API/SDK/GridCrew 是否读取 stable type keys、schema checksum 和语义视图；外部消费者兼容窗口 | M7 验收和联合契约冻结时校准 |
| M9 | CALIBRATED | equipment-rca-pack 使用公共类型/依赖/映射；以跨 Pack 问题验证复用价值；专家确认术语/映射 | ADR-0029/0030 已校准；9 份资料准入、真实 Pack 安装和 4 份 Source→Compile 技术试点完成，专家映射/评审仍为 P0，GridCrew 联合试点延期 |
| M10 | TARGETED | 语义模型的组织/空间所有权、继承、显式拒绝、发布/映射职责分离；禁止跨空间隐式共享草稿 | R2 下发前校准 |
| M11 | MANDATORY | 类型层级/映射的查询与影响分析、时间切片和投影重建；是否需专用图引擎必须测量，推理能力另立 ADR | M10 验收后详细校准 |
| M12 | TARGETED | 语义组合、层级展开、mapping 查询、索引重建的容量/性能/HA/DR；Schema/Pack 恢复一致性 | M11 验收后按实测校准 |
| M13 | MANDATORY | 私有 Pack 的命名空间、依赖、语义兼容、签名/撤销、供应链、迁移和发布治理 | M12 验收后详细校准 |
| M14 | MANDATORY | 多应用/GridCrew 绑定 fixed Release + SchemaVersion；语义兼容通知、Skill 升级和反馈候选闭环 | M13 验收及 GridCrew 契约可用后详细校准 |
| M15 | TARGETED | 语义模型运维、升级/回滚、客户迁移、文档、SLA、试点 KPI 和商业验收 | M14 验收后按交付范围校准 |

## 4. 各 Milestone 强制更新点

### M5：LLM 知识编译与 Wiki

- CompileRequest/CompileJob 固定 `schema_version_id`、`composition_checksum`、PromptVersion、ModelProfile 和 SourceVersion 集合；运行中不可替换。
- 结构化输出必须使用 stable type/relation/property keys，不以显示名称作为身份。
- entity normalization 先使用已发布 TypeTerm/ConceptMapping；歧义返回候选或人工映射，不静默选择。
- 未知类型、术语或 mapping 只创建 SemanticChangeProposal，不能修改当前 SchemaVersion 或让本次结果绕过 Schema。
- Wiki/Page/Entity 草稿保存生成它们的 SchemaVersion/type key；重编译基于稳定 ID 和版本，不按标题合并。
- 评测比较 schema-only 与 semantic constraints 的合规率、歧义率、人工修正率；阈值由授权负责人批准，不预设虚假数字。

### M6：Claim、Evidence、Conflict 与审核

- 明确三类问题：`SEMANTIC_INVALID`（违反模型）、`KNOWLEDGE_CONFLICT`（事实不兼容）、`EVIDENCE_INSUFFICIENT`（证据不足），不得互相替代。
- Claim predicate、RelationType 和 Entity type refs 固定到生成时 SchemaVersion；Schema 升级不原地重写待审/已审对象。
- EXACT mapping、父类型改变和破坏性语义迁移若进入人工审核，必须保存 ReviewAction/Approval/理由和影响报告。
- Evidence 继续支持/反对 Claim/Relation；Type/Mapping 的来源与审核是治理 provenance，不冒充事实 Evidence。

### M7：质量、Release、图谱与 Query

- Release manifest 固定 schema version、composition checksum、精确 PackVersion/checksum、规范化算法和投影配置。
- Release gate 阻断语义不合规、悬空 type key、未决阻断 mapping/Schema conflict；不把 LLM 置信度当门禁证据。
- Graph traverse 可按固定 SchemaVersion 展开 subtype 和显式 mapping，但类型层级不是实例 Relation。
- Query 每次只绑定一个固定 Release；回答/图结果记录所用语义快照，旧 Release 在新 Schema/Pack 发布后仍可复现。
- 搜索、向量和图索引包含 schema/release 维度并可由 Release 重建。

### M8：连接器、Obsidian 与 GridCrew 首期

触发条件：若外部客户端需要按 stable type key 过滤、解释关系或显示 Schema 信息，则必须扩展 OpenAPI/SDK/Event，并冻结兼容窗口；否则只返回 Release 内已固化知识，不开放草稿语义管理 API。

- GridCrew Skill 绑定 `tenant_id/space_id/release_id/policy_version`，并可读取 release schema/composition metadata；不得绑定可漂移“当前本体”。
- Connector 字段映射与 ConceptMapping 分离：前者是外部字段接入，后者是语义概念关系，不能共用状态或自动互相生成。
- Obsidian 导出可携带 stable keys/checksum，但回导只能形成 diff/候选，不能修改发布 Schema/Release。

### M9：Equipment RCA Pack 与联合试点

- equipment-rca-pack 依赖公共/core 语义定义，不把 Equipment/Component/Fault 等写入平台核心。
- 至少再引入一个 maintenance/operation/safety 小 Pack 或受控 fixture，验证公共概念复用和跨 Pack 查询，而不是只展示单 Pack 类型树。
- KKS、设备编码、术语和同义词仍为 Pack/企业扩展；专家审核 EXACT/BROADER/NARROWER mapping。
- 试点评估重复概念率、歧义处理、跨 Pack 查询正确性、编译合规和人工修正负担；门槛仍由产品/RCA 专家批准。

### M10：企业治理与多空间

触发条件：需要组织级共享语义模型、空间继承或企业级 Pack 时，必须冻结所有者、可见性、继承/覆盖和显式拒绝。默认不允许一个空间读取或修改另一个空间草稿，也不允许租户级定义静默覆盖空间发布版本。

### M11：高级检索与知识图智能

- 类型层级和 ConceptMapping 可参与查询改写、路径约束、影响分析和时间切片，但必须绑定固定 Release/SchemaVersion。
- 专用图数据库仍是可重建投影；是否引入由 ADR-0006 的实测门槛决定。
- RDF/OWL/SPARQL、规则推理或 OntologyVersion 不得以“图智能”名义顺带加入；触发重新评估条件时必须新 ADR。
- 增量编译的影响范围必须能解释由哪个 stable key、层级、mapping 或 Pack 变更触发。

### M12：规模、HA/DR 与国产化

触发条件：M11 实测表明语义展开/组合成为显著负载，或恢复流程涉及 Schema/Pack Registry。

- 容量模型加入 schema definition count、type/property/relation type count、hierarchy edge count、mapping count、Pack dependency depth 和 composition time。
- 灾备验证恢复后 schema snapshot、Pack artifacts、composition checksum、Release manifest 和投影一致。
- 国产数据库/中间件适配不得改变 stable key、checksum canonicalization 或版本语义。

### M13：私有 Domain Pack 生态

- Registry 强制发布者命名空间、不可变版本/checksum、依赖锁定、签名/撤销、许可证和 SBOM。
- 兼容检查覆盖 stable key 改义、层级/端点/mapping 变化、依赖冲突和下游 Schema/Release 影响。
- 私有 Pack 不能执行任意代码，也不能声明平台/他人命名空间为自己所有。
- Pack 市场/Registry 状态与空间 Installation、SchemaVersion 分离；撤销不删除历史 Release。

### M14：多应用与 GridCrew 深度闭环

- Application/Skill 固定 Release 和 schema composition metadata；升级必须做语义兼容检查并可灰度/回滚。
- Feedback/案例可生成 Source、知识草稿或 SemanticChangeProposal，但不能直接修改发布 Schema 或 Release。
- 事件/Webhook 的 Schema/Pack 升级通知只携带最小版本/checksum/兼容摘要，消费者按版本幂等处理。

### M15：商业发布与运营移交

触发条件：交付范围包含语义模型/Pack 治理。

- 运维手册覆盖 Schema/Pack 发布、升级、回滚、撤销、恢复和审计；客户迁移不改历史 Release。
- 产品文档使用“语义模型”而非承诺完整 Ontology 平台；明确不含自动推理、RDF/OWL IDE 等边界。
- 商业验收指标来自 M9/M11/M12 实证，不以类型数量或“有本体”作为成功标准。

## 5. 每次任务书校准检查表

- [ ] 最近 Milestone 已正式验收，状态与代码/迁移/测试一致；
- [ ] 是否修改 SchemaVersion、stable key、Pack 组合或 Release manifest；若是，ADR 是否更新；
- [ ] 对象、状态、权限、错误、API、Event、Workflow、SDK 是否一致；
- [ ] 旧 Schema/Pack/Release/Workflow history 是否可复现；
- [ ] 是否把语义合规、事实正确和 Evidence 明确分离；
- [ ] 是否存在自动合并、安装顺序覆盖或双版本权威；
- [ ] 是否有真实 fixture/E2E/安全/迁移证据，而非 Mock/固定 JSON；
- [ ] 需求追踪、风险、未决事项和停止声明是否同步。

## 6. 当前停止声明

本矩阵仅冻结后续影响，不构成 M4—M15 的正式下发。M3 已正式验收；除已校准的 M4 任务书外，不提前把未验证实现细节写入 M5—M15 正文。
