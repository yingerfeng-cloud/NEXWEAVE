# ADR-0022: M4 语义模型、SchemaVersion 权威与 Domain Pack 组合

- Status: Accepted
- Approval basis: 用户于 2026-08-29 明确要求先执行“M4 语义模型治理校准”，冻结 ADR、对象关系、版本权威、Pack 组合规则和后续任务影响；ADR-0005—0009、0013—0016、已验收 M0—M3 基线
- Date: 2026-08-29
- Decision owners: 产品/架构/知识工程负责人
- Related: NXW-SEMANTIC-001, NXW-SCHEMA-001/002, NXW-PACK-001/002, OQ-SEMANTIC-001—007, `SEMANTIC_MODEL_BASELINE.md`, `SEMANTIC_MODEL_IMPACT_MATRIX.md`

## Context

NEXWEAVE 已冻结 `SchemaVersion`、`EntityType`、`RelationType`、术语、Domain Pack、Entity、Relation、Claim、Evidence 和不可变 Release，但尚未冻结跨 Pack 的稳定概念身份、类型继承、语义映射、组合冲突和有效语义快照。若 M4 只实现彼此独立的实体/关系 Schema，不同 Pack 会重复声明 Equipment/Device/Asset、Fault/Failure 等相近概念，并把跨域对齐留给 Prompt 或 LLM 临时判断。

完整 Ontology 平台、RDF/OWL/SPARQL、描述逻辑推理和专用图数据库不是 R1 已批准目标。另建 `OntologyVersion` 又会与现有 `SchemaVersion` 形成双版本权威，使 Compile、Release、Pack 安装、迁移和查询必须联合锁定两套生命周期。

M3 已于 2026-08-29 正式验收。本 ADR 只冻结 M4 及后续治理语义，不表示 M4 已下发、已开始或已实现。

## Decision questions

1. R1 是否新增独立 `OntologyVersion`，还是由 `SchemaVersion` 承载有效语义快照？
2. 类型、属性、层级、术语和跨 Pack 映射如何形成单一权威？
3. 多个 Domain Pack 如何组合、冲突、升级、回滚并保持 Release 可复现？
4. LLM 建议语义模型时如何继续遵守 Schema Before Generation 与 Human in the Loop？

## Options

1. 不增加语义能力，只使用互相独立的 Schema 和术语；
2. 建立完整 Ontology 平台和独立 `OntologyVersion`；
3. 把 Ontology 作为逻辑语义层，以不可变 `SchemaVersion` 作为 R1 唯一有效语义快照，并通过声明式 Pack 组合生成；
4. 仅在 Prompt 中描述领域语义，不形成平台契约。

## Decision

选择 3。

### 1. 产品与版本权威

- 产品能力统一称为 **Semantic Model / 语义模型**；Ontology 是其概念层，不新增一级“本体平台”产品域。
- R1 不新增 `OntologyVersion` 聚合、表、公共 API 或独立发布生命周期。
- `SchemaDefinition` 是空间内稳定身份；不可覆盖的 `SchemaVersion` 是类型、属性、关系、层级、术语、映射、模板和规则解析后的唯一有效语义快照。
- CompileJob 必须锁定一个 `PUBLISHED` SchemaVersion；Release manifest 必须锁定精确 `schema_version_id`、`composition_checksum` 及组成它的 PackVersion/checksum 清单。
- “Semantic Model”是 SchemaVersion 的产品视图和逻辑投影，不是另一份可漂移的状态。

### 2. 对象关系

- `EntityType` 表达实体实例可绑定的类型；使用空间内稳定、命名空间化的 `type_key` 跨 SchemaVersion 识别同一概念。版本行 ID 不替代稳定语义 key。
- `PropertyDefinition` 是 EntityType 内的版本化子定义，具有稳定 `property_key`、数据类型、基数、必填、默认值、枚举/引用和合并策略；不拥有独立发布生命周期。
- `TypeHierarchyEdge` 表达 `child_type_key subTypeOf parent_type_key`。R1 允许有向无环多父层级；继承约束冲突必须阻断组合，禁止隐式优先级和循环。
- `RelationType` 使用稳定 `relation_type_key`，显式声明 domain/range、方向、基数、逆关系候选、因果标识、时效和 Evidence 要求。
- `TypeTerm` 绑定类型或关系类型，记录语言、规范词、别名、缩写、适用范围和歧义策略；同名、翻译或缩写不自动表示概念等价。实例级 `EntityAlias` 与类型级 TypeTerm 分离。
- `ConceptMapping` 保留来源/目标稳定 key，映射种类限定为 `EXACT`、`BROADER`、`NARROWER`、`RELATED`。映射必须有来源、版本、提出者和审核状态；`EXACT` 不物理覆盖来源定义，也不能仅由字符串相似度自动确认。
- `SchemaCompositionReport` 固化输入 Pack、依赖解析、规范化定义、冲突、兼容性、影响范围和 `composition_checksum`，是发布前审查证据，不替代 SchemaVersion。
- Taxonomy 由 TypeHierarchyEdge 表达；Constraint 由 PropertyDefinition、RelationType、Schema 校验和 LintRule 共同表达，不新增重复的 Taxonomy/Constraint 聚合。

### 3. Pack 组合规则

- 组合层次固定为：平台公共契约约束 → 已签名 PackVersion 依赖 DAG → 空间本地声明扩展 → 解析后的 SchemaVersion。
- 依赖范围必须在安装前解析为精确 PackVersion/checksum；依赖图必须无环，并以确定性拓扑序组合。
- Pack 内容不可被安装过程原地改写。空间扩展产生新的本地声明和 SchemaVersion，不修改原 Pack 制品。
- 同一稳定 key 的完全相同规范定义可复用；新增可选术语、兼容属性或子类型可作为兼容扩展。重复 key 且定义不兼容、继承冲突、端点/基数冲突、歧义 `EXACT` 映射或依赖版本冲突必须生成显式冲突并阻断发布。
- 禁止“后安装覆盖先安装”。任何映射、取代、弃用或迁移都必须声明、可审计并进入影响报告。
- Pack 安装 Workflow 先验证制品、签名、依赖和语义组合，再生成新的 `DRAFT` SchemaVersion；安装成功不等于 Schema 已发布。Schema 发布需要独立授权和审批。
- Pack 升级总是重新组合并生成新 SchemaVersion。卸载/禁用停止后续使用但不删除历史 Schema、知识或 Release；回滚恢复先前安装/Schema 指针并保留审计。

### 4. 兼容与迁移

- 一般兼容：新增可选类型/属性/关系/术语、增加不收紧既有实例的子类型、增加 `RELATED` 映射。
- 默认破坏性：删除/改义稳定 key，新增必填属性，缩窄数据类型/枚举/基数/domain/range，改变唯一键/合并策略/Evidence 要求，改变已使用的父类型，新增或改变 `EXACT` 映射，改变导致既有实例失配的继承约束。
- 破坏性变化不得直接发布，必须生成受影响 Entity/Relation/Claim/Page/Release 和 Pack 清单、声明式迁移计划、测试结果与人工批准。
- 已发布 SchemaVersion、PackVersion 和 Release 不原地修改；修正生成新版本。

### 5. AI、Evidence 与边界

- M4 不以 LLM 调用作为语义模型成立的前提；M5 可经 Model Gateway 生成 Type/Term/Mapping 建议。
- LLM 建议只进入下一 SchemaVersion 草稿，不能修改当前 PUBLISHED SchemaVersion、PackVersion 或 Release，也不能依据名称相似度自动合并概念。
- 编译必须先绑定已发布 SchemaVersion。编译中发现的未知概念只形成 `SemanticChangeProposal` 候选，审核发布后才能供后续编译使用。
- Schema 合规只证明表达符合语义契约，不证明 Claim/Relation 为真；正式 Claim 和因果 Relation 的 Evidence 规则保持不变。
- R1 不建设 RDF/OWL/SPARQL IDE、描述逻辑推理机、任意规则执行、完整图谱运维平台或图数据库权威源。

### 6. API、事件、Workflow 与 UI 边界

- 公共 API 继续以 `/schemas` 和 `/domain-packs` 为资源权威；不新增 `/ontologies` 双重入口。语义模型读取、组合和影响预览作为 SchemaVersion 子资源或表示。
- M4 事件至少记录 SchemaVersion 发布和 Pack 安装事实，并携带 `composition_checksum` 与最小 Pack 版本引用；事件不携带完整模型或敏感 Pack 内容。
- 复用 `DomainPackInstallWorkflow` 聚合但以 `nexweave.domain-pack-install.v2` 承载 M4 业务语义；M2 `v1` Kernel Stub 保留注册与历史 Replay，禁止改义。不得新增 Ontology Workflow。Workflow 保持确定性，制品读取、签名、依赖解析、持久化和影响分析位于幂等 Activity。
- Schema Studio 可展示“语义模型”视图：类型层级、属性、关系、术语、映射、版本差异和组合冲突；不新增独立完整 Ontology Studio。

## Consequences

正面：复用既有 Schema/Pack/Release 权威，避免双版本；为跨 Pack 语义复用、稳定编译和 Agent 消费提供显式契约；保持 PostgreSQL/Relation 表与声明式安全边界。

负面：M4 比原任务书增加稳定 key、层级、术语/映射、组合和影响分析，需要更多契约、迁移、UI 与测试；多父继承和跨 Pack 冲突需要严格确定性校验。

## Migration risks

- M4 尚未实现 Schema 表，当前引入逻辑语义的历史数据迁移成本较低；但一旦 M5 产生 Entity/Relation，稳定 key 与版本关系再变化将显著增大迁移风险。
- 若未来出现独立语义模型生命周期、同一模型服务多个独立 Schema、外部 RDF/OWL 无损往返或逻辑推理需求，必须以新 ADR 评估 `OntologyVersion`，不能在现有字段上静默扩张。
- 若 API 暴露 Provider/本体格式专用语义，后续难以替换；内部模型不得依赖 RDF、OWL、SPARQL 或图数据库 SDK。

## Validation

M4 至少以两个声明式 Pack/fixture 验证：稳定概念复用、依赖 DAG、同名歧义不合并、循环/继承冲突、破坏性变更阻断、确定性 composition checksum、安装/升级/回滚不删历史、恶意/可执行 Pack 拒绝。M5/M7/M9 分别验证语义约束编译、固定 Release 复现与跨 Pack 试点价值。

本 ADR 的 Accepted 状态表示治理决策已由用户明确要求冻结；M3 已另行正式验收，但不表示 M4 已下发或任何 M4 功能已实现。
