# Semantic Model Baseline

> 状态：ADR-0022/0023 已冻结并实现 M4 语义模型；实施、独立审查修复、本地技术验收及用户正式验收于 2026-08-30 完成，当前停止在已验收 M4，M5 未下发。

## 1. 定位

NEXWEAVE 的 Semantic Model 是知识编译、治理、发布和消费之间的统一语义契约。它在概念上区分“企业世界中的类型/关系”与“知识如何结构化表达”，但 R1 不建立独立 `OntologyVersion` 权威：解析后的完整语义模型由不可变 `SchemaVersion` 承载。

```text
DomainPackVersion(s) + Space-local declarations
                    ↓ deterministic compose / validate
          immutable effective SchemaVersion
            ├─ EntityType / PropertyDefinition
            ├─ TypeHierarchyEdge
            ├─ RelationType
            ├─ TypeTerm / ConceptMapping
            ├─ PageTemplate / LintRule
            └─ composition inputs + checksum
                    ↓
        CompileJob / Entity / Relation / Claim
                    ↓
              immutable Release
```

## 2. 权威对象关系

| 对象 | 稳定身份与版本 | 归属关系 | 权威规则 |
|---|---|---|---|
| SchemaDefinition | `schema_definition_id` | tenant/space；拥有多个 SchemaVersion | 稳定聚合身份，不承载可变模型正文 |
| SchemaVersion | `schema_version_id` + version + checksum | 属于一个 SchemaDefinition | 类型、层级、术语、映射、模板、规则和组合输入的不可变有效快照；R1 唯一语义版本权威 |
| EntityType | 版本行 ID + 稳定 `type_key` | SchemaVersion 内 | `type_key` 跨版本识别同一概念；实例 Entity 绑定生成它的 SchemaVersion/type key |
| PropertyDefinition | 版本行 ID + 稳定 `property_key` | EntityType 内 | 随 SchemaVersion 固化，不独立发布 |
| TypeHierarchyEdge | child/parent type key | SchemaVersion 内 | `subTypeOf` DAG；禁止循环；多父继承冲突阻断发布 |
| RelationType | 版本行 ID + 稳定 `relation_type_key` | SchemaVersion 内 | 固化 domain/range、方向、基数、时效、因果和 Evidence 约束 |
| TypeTerm | term key + language + scope | EntityType/RelationType 内 | 类型级词汇；名称相同不自动等价；与实例 EntityAlias 分离 |
| ConceptMapping | mapping ID + source/target key + kind | SchemaVersion 内，可引用输入 Pack 定义 | `EXACT/BROADER/NARROWER/RELATED`；保留来源身份和审核事实，不物理覆盖 |
| SchemaCompositionReport | report ID + input hash + result checksum | 一个候选 SchemaVersion | 发布前组合、冲突、兼容和影响审查证据；不是第二版本权威 |
| DomainPackVersion | pack ID/version/checksum | 不可变声明制品 | 可提供类型、属性、关系、术语、映射、模板和规则；不可执行任意代码 |
| Installation | installation ID/version/state | tenant/space + 精确 PackVersion | 记录安装/升级/回滚事实，不成为语义定义权威 |

## 3. 稳定 key 与命名空间

- `type_key`、`relation_type_key` 和 `property_key` 使用发布者/Pack/本地空间可区分的规范命名空间；显示名称、翻译和文件路径不得充当稳定身份。
- Pack 发布后，其稳定 key 不得在同一 major 内改义或复用；重命名显示文案通过 TypeTerm，概念取代通过显式 mapping/deprecation。
- 空间本地声明不得伪造其他发布者命名空间。跨 Pack 复用通过依赖引用或 ConceptMapping，不通过复制后同名推断。
- M4 具体字符集、长度、大小写规范和保留命名空间在公共 contracts 中冻结并由 JSON Schema/领域测试执行。

## 4. 类型、属性与关系

- EntityType 层级为有向无环图。多父类型的继承约束按交集合并；数据类型、必填、基数、唯一键、默认值或引用目标不兼容时停止组合并产生冲突。
- 属性只在所属 EntityType 及其兼容子类型中生效。属性显示名变化不改变 property key；收紧约束默认属于破坏性变更。
- RelationType 必须引用同一候选 SchemaVersion 中可解析的 domain/range type key；跨 Pack 端点在组合后解析，不保留悬空引用。
- 类型层级不是实例 Relation；`Pump subTypeOf Equipment` 属于 SchemaVersion，`Pump-001 belongsTo System-A` 才是知识 Relation。
- 语义合规不等于事实正确。Claim/Relation 的 Evidence、审核和 Release 门禁继续独立执行。

## 5. 术语与映射

| 能力 | 规则 |
|---|---|
| 规范词 | 每个 language/scope 至多一个 preferred term；冲突必须显式解决 |
| 别名/缩写 | 只影响识别和展示；不能单独证明概念等价 |
| EXACT | 经审核的强映射；仍保留 source/target 身份；约束不兼容时禁止成立 |
| BROADER/NARROWER | 表达跨命名空间概念粒度关系；不自动改写本地类型层级 |
| RELATED | 仅表达相关性；不能用于实例去重或类型替换 |
| 歧义 | 同一词指向多个 type key 时保留歧义，编译必须给出候选或进入人工映射，不静默选择 |

## 6. 确定性 Pack 组合

1. 校验 manifest、内容 checksum、签名、平台兼容和禁止执行内容；
2. 将依赖版本范围解析为精确 PackVersion/checksum，拒绝缺失、循环和不唯一解析；
3. 按确定性拓扑序装载声明；同层按规范 stable key 排序，禁止依赖安装时间决定结果；
4. 规范化类型、属性、关系、术语和映射，执行稳定 key、引用和 DAG 校验；
5. 对重复 key 执行结构兼容检查；不兼容项形成阻断冲突，不使用“最后写入获胜”；
6. 应用空间本地声明扩展；本地扩展不能修改 Pack 制品，只能形成候选 SchemaVersion 的增量；
7. 生成 SchemaCompositionReport、规范化快照和 `composition_checksum`；相同输入必须产生相同 checksum；
8. 生成新的 DRAFT SchemaVersion，经测试、影响预览和批准后方可发布。

组合输入至少固化：平台契约版本、基础 SchemaVersion（如有）、精确 PackVersion/checksum 列表、本地声明 checksum、规范化算法版本和映射/迁移声明版本。

## 7. 生命周期与版本

```text
DRAFT → TESTING → PUBLISHED → DEPRECATED
```

- SchemaVersion 发布后不可覆盖；修正或 Pack 变化产生新版本。
- Pack 安装成功只表示声明已验证并生成候选配置，不自动发布 SchemaVersion。
- CompileJob 仅可锁定 PUBLISHED SchemaVersion；运行中不得替换。
- Release 固化 schema version、composition checksum、PackVersion/checksum、Prompt/Model 和投影配置；历史 Release 不因 Pack 禁用或升级而变化。
- Pack 回滚和 Schema 回滚仅恢复先前指针/安装状态，不删除历史定义、知识、报告或 Release。
- AI/人工在编译过程中发现的新概念形成下一版本的 SemanticChangeProposal；不得写入当前发布版本。

## 8. 兼容分类

| 类别 | 示例 | 默认处理 |
|---|---|---|
| 兼容 | 新增可选类型/属性/关系/术语；新增不收紧既有约束的子类型；新增 RELATED mapping | 可进入常规验证，仍需版本和影响报告 |
| 条件兼容 | 新增父类型、EXACT/BROADER/NARROWER mapping、增加逆关系、改变默认值 | 必须扫描既有草稿/知识并人工确认 |
| 破坏性 | 删除或改义 stable key；新增必填；缩窄类型/枚举/基数/domain/range；改变唯一键/合并/Evidence；造成继承冲突 | 阻断直接发布；要求迁移计划、测试和批准 |

## 9. 权限、审计和安全

- 复用 `schema.read/edit/validate/publish` 与 `pack.read/install/rollback` 权限；语义映射和 Schema 发布不得因 UI 可见而绕过服务端授权。
- Schema/Pack 写入使用 tenant/space 作用域、ETag、幂等、AuditLog 与 Outbox；发布和高风险映射遵守职责分离。
- Pack、术语、Prompt、样例和迁移声明均视为不可信输入；禁止远程 include、路径穿越、宏、脚本、二进制和任意模板执行。
- `HIGHLY_RESTRICTED` 资料不得为了生成语义建议发送到外部模型；LLM 建议必须经 Model Gateway、密级策略、审计和人工审核。

## 10. R1 不做

- 独立 OntologyVersion 生命周期或 `/ontologies` 公共资源；
- RDF/OWL/SPARQL 编辑器、描述逻辑推理、任意规则执行；
- 将图数据库、向量库或 LLM Prompt 作为语义权威；
- 因同名、翻译、向量相似或 LLM 置信度自动合并类型；
- 要求客户先完成完整企业本体才能导入资料或获得基础价值。

## 11. 独立 OntologyVersion 的重新评估触发器

只有出现至少一项并取得实际证据时，才以新 ADR 评估拆分：

- 同一语义模型需要独立服务多个 Schema，并具有独立发布/审批节奏；
- 必须与 RDF/OWL/SKOS 等外部标准无损往返；
- 业务需要超出类型/约束校验的逻辑蕴含与推理；
- 同一概念模型需要生成多个独立知识表示或存储投影；
- Ontology 与 Schema 由不同治理组织独立拥有和发布。

## 12. 验证基线

M4 最低需要覆盖：两个 Pack 的公共概念复用、同名歧义不合并、依赖循环、层级循环、多父约束冲突、映射冲突、确定性 checksum、破坏性变更影响报告、安装/升级/禁用/回滚不删历史、跨租户/空间授权和恶意 Pack 拒绝。完整门禁由校准后的 M4 任务书定义。
