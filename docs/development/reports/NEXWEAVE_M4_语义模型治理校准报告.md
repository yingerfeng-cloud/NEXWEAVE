# NEXWEAVE M4 语义模型治理校准报告

## 1. 总体结论

- 校准结论：**通过**。M4 的语义模型定位、对象关系、版本权威、Domain Pack 组合、兼容/迁移、安全边界和后续 Milestone 影响已形成一致治理基线。
- 阶段结论：**不构成 M4 下发或实现验收**。M3 已完成本地验证但仍待用户正式验收；在用户明确验收 M3 并下发 M4 前，不得创建 M4 代码、迁移、API、事件、SDK、Workflow 或 UI。
- 产品取舍：R1 引入轻量、可治理的 Semantic Model，但不建设完整本体建模平台。若未来出现独立生命周期、外部标准无损往返或逻辑推理等真实需求，必须以新 ADR 重新评估。

## 2. 已冻结决策

1. **单一版本权威**：不可变 `SchemaVersion` 是 R1 唯一有效语义快照；Semantic Model 是其逻辑视图，不新增 `OntologyVersion`、`/ontologies` 或第二套发布状态。
2. **对象关系**：复用 `EntityType`、`RelationType`，增加版本内 `PropertyDefinition`、`TypeHierarchyEdge`、`TypeTerm`、`ConceptMapping` 和 `SchemaCompositionReport`。stable key 跨版本识别概念，数据库行 ID 不充当语义身份。
3. **层级与映射**：类型层级允许无环多父结构；继承约束冲突必须阻断。映射限定 `EXACT/BROADER/NARROWER/RELATED`，同名、翻译、向量相似或 LLM 判断不得自动确认等价。
4. **Pack 组合**：平台约束、精确 PackVersion 依赖 DAG、空间本地声明按固定规则确定性组合；禁止后安装覆盖先安装。相同输入与算法版本必须生成相同 `composition_checksum`。
5. **安装与发布分离**：Pack 安装只验证制品、依赖和组合并生成候选 `DRAFT` SchemaVersion/报告；Schema 发布是独立权限和审批动作。
6. **历史可复现**：Pack 升级生成新 SchemaVersion；禁用、卸载或回滚不删除历史 Schema、知识、报告或 Release。CompileJob 和 Release 必须固定 SchemaVersion/composition/Pack 输入。
7. **真实性边界**：Schema 合规不等于事实正确，不替代 Claim/Relation 的 Evidence、冲突处理、专家审核和 Release 门禁。LLM 只能提出下一版本候选。
8. **Workflow 版本兼容**：M4 使用 `nexweave.domain-pack-install.v2`；M2 `v1` Kernel Stub 保留注册和 Replay，不得改写历史语义。

## 3. 本轮实际完成范围

- 新增 Accepted ADR-0022，记录方案、取舍、迁移风险和重新评估触发器；
- 新增 Semantic Model baseline，冻结对象拓扑、stable key、组合算法、版本、权限和 R1 非目标；
- 详细校准 M4 任务书，补齐前置条件、实现范围、API/Event/Workflow/SDK、迁移、安全、真实 E2E、验收和停止边界；
- 新增 M5—M15 影响矩阵，区分 `MANDATORY` 与 `TARGETED` 更新，并规定每阶段正式下发前再按最近验收实况精确校准；
- 同步产品、架构、领域、数据、API、事件、Workflow、C4、状态/权限/错误、Domain Pack、需求追踪、开放问题、项目状态、索引、任务 manifest 和变更日志；
- 未修改应用代码、数据库迁移、公共契约生成物、依赖、部署或运行数据。

## 4. M4 任务书的关键增量

- Schema Studio 从基础实体/关系编辑扩展为类型、属性、层级、关系、术语、映射、版本差异、组合冲突和影响预览；
- Domain Pack 从单包安装扩展为不可变版本、签名/信任、精确依赖、确定性组合、兼容分类、声明式迁移和历史保留；
- M4 最低真实验收至少需要 core、equipment-rca、maintenance 三类受控 fixture，验证公共概念复用、同名歧义、依赖/层级/继承/映射冲突和 checksum 确定性；
- 明确 M4 不建设 RDF/OWL/SPARQL IDE、描述逻辑推理机、独立本体数据库、任意 Pack 代码执行或领域专用核心分支。

## 5. 后续任务影响

| 阶段 | 处理方式 | 核心影响 |
|---|---|---|
| M5 | 必须详细校准 | Compile 固定发布 Schema/composition；输出 stable key；未知概念只形成变更候选 |
| M6 | 定向校准 | 区分语义不合规、事实冲突和证据不足；高风险 mapping/迁移进入审核 |
| M7 | 必须详细校准 | Release 固化 Pack/Schema 输入；Query/Graph 绑定固定语义快照 |
| M8 | 定向校准 | 外部 API/SDK/GridCrew 只消费固定 Release 及其语义元数据 |
| M9 | 必须详细校准 | RCA Pack 不进入核心，并以跨 Pack 复用和专家确认验证价值 |
| M10—M12 | 按治理/实测触发 | 组织/空间所有权、图智能边界、规模与灾备一致性 |
| M13—M14 | 必须详细校准 | 私有 Pack 供应链、多应用语义兼容与升级/回滚 |
| M15 | 按交付范围校准 | 客户迁移、运维、SLA 和商业指标来自前序实证 |

本轮不直接重写 M5—M15 正文，避免在 M4 尚未实现、验证前锁死物理模型和接口细节。影响矩阵是后续校准的强制输入，不是后续阶段的实施授权。

## 6. 数据库与迁移影响

- 本轮没有新增或修改迁移，数据库 revision 仍停留在 M3 的 `0004_m3_source_parsing`。
- M4 正式实施时只能追加新迁移，不得修改 `0001`—`0004`；候选表和约束已进入逻辑数据基线，但具体列、索引、唯一键和 revision 尚未实现。
- 由于 M5 尚未生成正式 Entity/Relation/Claim，当前冻结 stable key 与 SchemaVersion 权威的迁移成本最低；推迟到 M5 后再改变会显著增加历史对象迁移和 Release 复现风险。

## 7. 安全、权限与证据检查

- Domain Pack 保持纯声明式；禁止脚本、宏、二进制、远程 include、路径穿越和任意网络/Secret 访问。
- Pack 安装权不隐含 Schema 发布权；高风险发布、`EXACT` mapping 和破坏性迁移需要职责分离、审计和显式批准。
- PackVersion/checksum、组合输入、算法版本、冲突和影响报告须可审计；事件只传最小版本摘要，不泄漏敏感 Pack/Prompt/样例。
- Semantic Model 仅约束知识表达，不能充当 SourceAnchor、Evidence、专家确认或事实真实性证据。

## 8. 需求追踪

- 新增跨阶段 `NXW-SEMANTIC-001—004`；
- 更新 `NXW-SCHEMA-001/002`、`NXW-PACK-001/002` 为 `GOVERNANCE FROZEN；NOT IMPLEMENTED`；
- 关闭 `OQ-SEMANTIC-001—007`，分别记录版本权威、对象、层级、映射、Pack 组合、编译/Evidence 边界和后续校准策略；
- 精确 key 格式、Pack canonical source、签名/撤销算法和迁移 DSL 仍为 M4 编码前必须关闭的开放实现决策。

## 9. 验证结果

- `git diff --check`：通过，无尾随空白或补丁格式错误；
- 任务 manifest：`jq` 结构检查、版本/Release/ADR-0022 amendment 断言和清单文件存在性检查均通过；
- 治理一致性扫描：`OntologyVersion`/`/ontologies` 仅出现在禁止项、方案对比或未来新 ADR 触发器中；Domain Pack 安装 API 统一为 `/domain-pack-installations`；M4 Workflow 明确使用 v2 并保留 M2 v1 Stub Replay；
- 变更路径检查：`apps/`、`packages/`、`workers/`、`migrations/`、`scripts/`、`tests/`、部署、依赖和 CI 路径均无变更；
- 未运行产品测试、Compose 或数据库迁移，因为本轮没有产品实现或运行时变更。

## 10. 风险与开放项

### P0

- 无治理 P0。M4 未下发，因此“尚无实现”是阶段边界，不是本轮缺陷。

### M4 编码前必须关闭

- stable key 的字符集、长度、大小写和保留命名空间；
- Pack v1alpha1 的 YAML/JSON canonical source 与 checksum 规范；
- 签名、信任根、撤销和离线验证方案；
- 声明式迁移 DSL、回滚能力和资源预算。

### 后续重新评估触发器

- 独立语义生命周期、RDF/OWL/SKOS 无损往返、逻辑推理、多个 Schema 共享独立模型或不同治理组织独立发布语义模型。出现实际证据时新建 ADR，不得在 M11 或 Provider adapter 中静默引入。

## 11. 停止声明

本轮已停止在 **M4 语义模型治理校准**。M3 未被本轮自动验收，M4 未被正式下发；没有进入 M4 编码，也没有提前修改 M5—M15 实施任务书。
