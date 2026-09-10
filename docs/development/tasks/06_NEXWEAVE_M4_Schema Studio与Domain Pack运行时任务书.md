# NEXWEAVE M4：Schema Studio、语义模型与 Domain Pack 运行时任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台
> 产品版本：R1：可信知识闭环与联合试点版
> 建议周期：原 4—5 周；正式下发前须依据新增语义范围重新评估，不静默压缩测试与安全门禁
> 执行对象：Codex
> 状态：2026-08-30 M4 实施、独立审查修复、本地技术验收及用户正式验收完成；未下发或进入 M5
> 权威增量：ADR-0022、`SEMANTIC_MODEL_BASELINE.md`、`SEMANTIC_MODEL_IMPACT_MATRIX.md`
> 当前边界：M4 已授权实施；完成后必须停止，不授权进入 M5
> 阶段原则：M3 正式验收且用户明确下发 M4 后，只执行本 Milestone，完成后停止

---

## 1. 阶段定位

建立“先定义语义与知识结构，再生成知识”的平台核心：以不可变 SchemaVersion 作为 R1 唯一有效语义快照，通过声明式 Domain Pack 组合稳定类型、属性、层级、关系、术语、映射、模板和规则，并使破坏性变化在进入编译和 Release 前被识别、审查和阻断。

M4 提供轻量 Semantic Model 能力，但不建设独立 Ontology 平台。M4 不生成真实知识 Entity/Relation/Claim/Evidence，不执行 LLM 知识编译，也不进入审核、Release 或 Query。

---

## 2. 权威资料与前置条件

实施前必须完整读取并核对：

1. 用户当前指令、本任务书、根 `AGENTS.md`；
2. M3 正式验收记录、执行报告、迁移/运行手册和未关闭风险；
3. ADR-0005—0009、0013—0016、0020—0022 及架构/产品基线；
4. Semantic Model、Domain Model、Data、API、Event、Workflow、State/Permission/Error、Security、Dependency、Migration、Quality baseline；
5. Domain Pack Specification、需求追踪与语义模型影响矩阵；
6. PRD 8.4/8.14、原型 Schema Studio 信息架构和完整开发总纲。原型静态类型、固定 JSON、演示 Pack 和 LLM 文本不构成功能事实。

必须满足：

- M3 已由用户正式验收，SourceVersion、DocumentSegment、SourceAnchor 和 v2 Workflow 真实可用；
- 工作区已有修改已盘点并保护；
- ADR-0022 保持 Accepted 且无未记录权威冲突；
- OQ-PACK-UI-001 或其替代决策在前端编码前关闭；
- M4 具体 stable key 格式、canonical JSON/YAML、签名/撤销算法、迁移 DSL 最小语法在 contracts 编码前冻结；
- 任何新增依赖已记录用途、锁定版本、许可证、供应链风险和替代方案。

若 M3 未验收、Pack 签名/依赖验证不可真实运行、确定性组合无法证明或真实 PostgreSQL/Temporal 无法运行，对应纵向验收为 P0 阻塞；不得用内存配置、未签名目录、Mock Workflow 或固定结果冒充。

---

## 3. 阶段目标

1. 实现 SchemaDefinition/SchemaVersion 及不可变发布生命周期。
2. 实现 EntityType、PropertyDefinition、TypeHierarchyEdge、RelationType、TypeTerm、ConceptMapping、PageTemplate、LintRule、EvaluationSuite 的声明、校验和版本化。
3. 实现稳定语义 key、引用完整性、无环多父层级、关系端点/基数、术语歧义和映射规则。
4. 实现 Schema 组合、测试、发布、兼容分类、影响分析、迁移预览和 composition checksum。
5. 实现 Domain Pack manifest、签名、依赖 DAG、确定性组合、安装、升级、禁用、回滚和审计。
6. 交付至少两个最小声明式 Pack/fixture，用于证明公共概念复用、冲突阻断和不改平台代码安装；其中包含 equipment-rca-pack 最小样例，但不实现自动根因诊断。
7. 实现 Schema Studio 中的轻量“语义模型”视图，而非完整 Ontology Studio。

---

## 4. 不可变约束

1. Raw First：M4 不修改 M3 Raw、Segment 或 Anchor；Schema/Pack 不得携带或覆盖原始资料。
2. Schema Before Generation：CompileJob 只能锁定 PUBLISHED SchemaVersion；M4 不执行真实 Compile。
3. Single Semantic Authority：R1 不新增 OntologyVersion；SchemaVersion 是类型、层级、术语、映射、模板和规则的唯一有效快照。
4. Evidence Native：Schema 合规不证明事实为真；正式 Claim 与因果 Relation 的 Evidence 规则不变。
5. Human in the Loop：AI 只能建议未来草稿；Schema 发布、EXACT 映射和破坏性迁移需要授权人工决定。
6. Draft / Release Separation：DRAFT/TESTING/PUBLISHED 分离；发布版本不可覆盖。
7. Conflict Instead of Overwrite：重复 key、依赖、继承、关系端点或映射冲突必须显式阻断，禁止后安装覆盖先安装。
8. Version Reproducibility：SchemaVersion 固化 composition checksum、算法版本和精确 PackVersion/checksum 输入；后续 Release 可完整还原。
9. Platform / Domain Decoupling：平台核心只实现通用语义契约，不写死 Equipment、RCA、核电、泵、故障等概念。
10. Declarative Pack Only：Pack 不执行任意 Python/JavaScript/Java/Shell/二进制/宏或远程 include。
11. Reliable Workflow：Pack 安装/升级/回滚使用既有可靠 Workflow；Workflow 定义不直接 I/O。
12. Audit by Default：Schema/Pack/映射/发布/回滚/权限决定均审计，业务事务与 Outbox 同步记录。
13. GridCrew Boundary：M4 不实现 GridCrew 消费；未来只通过固定 Release/API/SDK 暴露语义。
14. Storage Boundary：PostgreSQL 是业务权威；RDF、图数据库、搜索和 UI 类型树只可为导出/投影。

---

## 5. 领域对象与语义关系

### 5.1 Schema 权威

- SchemaDefinition 保存空间内稳定身份和版本链。
- SchemaVersion 保存不可变规范化快照、状态、版本、content checksum、composition checksum、规范化算法版本和精确 Pack 输入。
- Semantic Model 是 SchemaVersion 的只读产品视图，不拥有第二套状态、数据库表或发布 API。

### 5.2 类型与属性

- EntityType 使用版本行 ID 和命名空间化稳定 `type_key`；显示名称/翻译不充当身份。
- PropertyDefinition 使用稳定 `property_key`，声明类型、必填、基数、枚举/引用、默认值、唯一键和合并策略；随 SchemaVersion 发布。
- TypeHierarchyEdge 表达 `subTypeOf` DAG。允许多父类型，但循环或继承约束冲突必须阻断组合。
- 类型层级不得保存为知识实例 Relation。

### 5.3 关系、术语与映射

- RelationType 使用稳定 `relation_type_key`，声明 domain/range、方向、基数、逆关系候选、因果、时效和 Evidence 要求。
- TypeTerm 记录规范词、别名、缩写、语言、范围和歧义；与 M5 EntityAlias 分离。
- ConceptMapping 只允许 `EXACT`、`BROADER`、`NARROWER`、`RELATED`；同名/翻译/向量相似/LLM 置信度不得自动建立映射。
- EXACT mapping 不物理合并来源定义；约束不兼容或一对多歧义时必须阻断。

### 5.4 组合与报告

- SchemaCompositionReport 固化输入、依赖解析、规范化定义、冲突、兼容分类、受影响对象/版本和 result checksum。
- 同一规范化输入必须产生相同 composition checksum；数据库返回顺序、安装时间和 Worker 调度不得改变结果。
- Report 是审查证据和查询事实，不替代 SchemaVersion。

---

## 6. Domain Pack 组合规则

组合顺序固定为：

```text
platform semantic contract
  → exact signed PackVersion dependency DAG
  → space-local declarative extensions
  → normalized DRAFT SchemaVersion + CompositionReport
  → validate/test/approve
  → immutable PUBLISHED SchemaVersion
```

1. manifest 中的版本范围必须在安装时解析为精确 PackVersion/checksum；缺失、循环、歧义或不兼容依赖阻断。
2. 依赖按确定性拓扑序组合；同层按规范 stable key 排序。
3. 同一 stable key 的规范定义完全一致时可复用；兼容扩展只允许增加不收紧既有约束的可选内容。
4. 不兼容重复 key、层级/继承冲突、悬空关系端点、歧义 EXACT mapping 和破坏性变更生成阻断冲突。
5. 禁止“最后写入获胜”和“后安装覆盖先安装”。覆盖、弃用、映射和迁移必须显式声明。
6. 空间本地扩展不修改 Pack 制品，只参与生成新的 SchemaVersion。
7. 安装 Workflow 成功只生成/关联候选 SchemaVersion；不能隐式调用 Schema publish。
8. Pack 升级重新组合并生成新 SchemaVersion；禁用/卸载不删知识；回滚恢复先前安装/Schema 指针并保留历史。

---

## 7. Schema 服务与 Studio

### 7.1 后端服务

- SchemaDefinition/Version 创建、读取、编辑草稿、验证、测试、发布和弃用；
- 类型/属性/层级/关系/术语/映射/模板/规则的 contract-first CRUD；
- stable key、引用、DAG、继承、端点、映射、术语歧义和安全校验；
- 组合预览、兼容分类、受影响 Entity/Relation/Claim/Page/Release 清单和迁移预览；M4 尚无真实知识表时以 schema/pack fixture 验证，并保留 M5+ adapter 边界；
- 发布采用审批、ETag、幂等、Audit/Outbox；PUBLISHED 内容不可修改。

### 7.2 前端

- Schema 列表、版本、状态、创建/编辑/验证/发布和 diff；
- “语义模型”视图：类型树/DAG、属性、关系、术语、映射、来源 Pack 和冲突；
- Pack 依赖/组合输入、影响报告、安装/升级/回滚状态；
- 所有页面由真实 API 驱动，支持深链接、刷新恢复、权限、空/加载/错误/冲突状态；
- R1 不实现 RDF/OWL/SPARQL IDE、任意代码组件或专业本体图形编辑器。

---

## 8. API、事件、Workflow 与 SDK

- 公共资源使用 `/schemas`、`/domain-packs` 和 `/domain-pack-installations`；不新增 `/ontologies`。
- 语义模型通过 SchemaVersion 子资源读取；compose/validate 返回 composition report、checksum、冲突和影响。
- 异步安装/升级/回滚返回 Installation ID、Workflow ID 和 Run ID；业务对象 ID 不使用临时线程 ID。
- `io.nexweave.schema.published.v1` 固化 schema/version/composition checksum/最小 Pack 引用。
- `io.nexweave.pack.installed.v1` 只表示安装事实和候选 Schema 引用，不表示 Schema 已发布。
- DomainPackInstallWorkflow 使用 `nexweave.domain-pack-install.v2` 承载 M4 业务；M2 `v1` Kernel Stub 保留注册与历史 Replay，不得改义。
- OpenAPI 3.1、JSON Schema Draft 2020-12、事件 payload、Python/TypeScript SDK 和 Web 类型必须由 canonical contracts 生成/校验并防漂移。

---

## 9. 数据、迁移与兼容

- 新增 additive M4 migration；不得修改 `0001`—`0004`。
- 候选表包括 schema definition/version、entity type、property definition、type hierarchy edge、relation type、type term、concept mapping、composition report、page template、lint/evaluation、domain pack/version、installation 及依赖/输入关联。
- 所有业务对象明确 tenant_id、space_id、稳定 key、版本、状态、创建者、时间和必要 checksum；复合外键阻断跨租户/空间引用。
- 真实 PostgreSQL 执行 M0→M4 upgrade、M4 down、再次 up，并验证 M0—M3 数据不变。
- 破坏性 Schema 变化必须阻断直接发布；迁移产生新草稿/对象版本，不修改历史 Release。
- 同 major API/Pack contract 只允许兼容扩展；删除、改义、收紧枚举/约束、版本/Release 语义变化必须新 ADR 和兼容窗口。

---

## 10. 安全、权限与错误

- 服务端执行 `schema.read/edit/validate/publish`、`pack.read/install/rollback`；Pack 安装权限不隐含 Schema 发布权限。
- 高风险 Schema 发布、EXACT mapping 和破坏性迁移遵守职责分离；创建者不得自动批准自己的高风险变更。
- Pack 的 manifest、YAML/JSON、术语、Prompt、模板、样例和迁移声明均为不可信输入；限制大小、深度、引用、模板能力和资源预算。
- 禁止路径穿越、绝对路径、符号链接逃逸、远程 include、宏/脚本/二进制、未声明网络或 Secret。
- 所有错误使用 `application/problem+json` 和稳定 code，至少覆盖 `SEMANTIC_MODEL_INVALID`、`SEMANTIC_MAPPING_AMBIGUOUS`、`SCHEMA_BREAKING_CHANGE`、`PACK_DEPENDENCY_CONFLICT`、`PACK_COMPOSITION_CONFLICT`、签名/制品/权限/版本冲突。
- 事件、日志、trace 和报告不得泄漏完整敏感 Pack 内容、Prompt、样例或 HIGHLY_RESTRICTED 资料。

---

## 11. 测试、E2E 与门禁

### 11.1 自动化矩阵

- 单元：stable key、类型/属性/关系、DAG、继承冲突、术语歧义、mapping、兼容分类、状态机；
- 契约：OpenAPI、JSON Schema、事件、SDK、Pack manifest/canonicalization；
- 确定性：相同输入跨进程/重试/顺序扰动产生相同 composition checksum；
- 集成：真实 PostgreSQL、Temporal、对象/Registry adapter、签名/撤销边界；
- Workflow：依赖重试、重复安装、取消、失败补偿、升级、回滚、Worker 恢复、Stub Replay；
- 安全：恶意 Pack、路径穿越、远程 include、脚本/宏/二进制、签名错配、资源炸弹、跨租户/空间、越权发布；
- Web：版本/类型/层级/关系/术语/映射/组合/冲突/发布/安装的真实 API 流程和可访问性；
- 迁移：真实 PostgreSQL up/down/up 与 M0—M3 数据兼容。

### 11.2 必须真实验证的纵向链路

1. core fixture + equipment-rca-pack 复用公共 Equipment type key，安装不修改平台代码；
2. 第二个 maintenance fixture 依赖 core 并扩展可选类型/关系，确定性生成同一 checksum；
3. “故障/Fault/Failure”同名/近义歧义不自动合并，产生待处理 mapping；
4. 依赖循环、类型层级循环、多父属性冲突、关系端点冲突、EXACT mapping 冲突分别被阻断；
5. 破坏性变更生成影响报告和迁移预览，不能直接发布；
6. Pack 安装生成 DRAFT SchemaVersion，授权发布后才产生 PUBLISHED 版本；
7. 升级/禁用/回滚保留历史 Schema、Pack、报告、审计和固定引用；
8. 恶意/未签名/篡改 Pack、越权与跨空间组合被真实拒绝。

测试证据必须记录命令、环境、输入 checksum、期望/实际状态、业务/Workflow ID 和未执行项；Mock、静态 UI 和固定 JSON 不能作为纵向验收。

---

## 12. 阶段交付物

- Schema/Semantic Model 领域、契约、数据库、API、事件、SDK 和真实 Web；
- Domain Pack v1alpha1 规范、签名/依赖/组合/安装 Workflow 和 CLI/SDK；
- core/equipment-rca/maintenance 最小声明 fixture，且领域概念不进入平台核心；
- SchemaCompositionReport、兼容/迁移/安全/供应链报告；
- additive migration 与真实 up/down/up 证据；
- 自动化测试、真实 E2E、故障/安全证据；
- ADR/baseline/需求追踪/CHANGELOG/STATUS/用户与开发文档更新。

---

## 13. 最低验收标准

- [x] M3 已正式验收且 M4 未越界修改 Raw/Anchor/Source 语义；
- [x] R1 只有 SchemaVersion 一个有效语义版本权威，无 OntologyVersion 双状态/API；
- [x] 稳定 key、属性、类型 DAG、RelationType、TypeTerm、ConceptMapping 均有真实领域/契约/数据库/API 闭环；
- [x] 至少两个 Pack/fixture 可复用公共概念并确定性组合，相同输入产生相同 checksum；
- [x] 同名歧义、依赖/层级/继承/端点/mapping 冲突均不会静默覆盖；
- [x] 破坏性变更被阻断并产生可审查影响/迁移报告；
- [x] 安装不自动发布 Schema，升级/禁用/回滚不删除历史知识或版本；
- [x] 恶意/可执行/篡改 Pack、越权和跨租户/空间操作被拒绝并审计；
- [x] OpenAPI/Event/SDK/Web/Workflow/迁移与本地全局门禁通过；远程 CI 未在无提交/push 授权下伪称执行；
- [x] M4 无新增依赖；既有锁定依赖用途、许可证、风险和替代方案不变，本地生产依赖审计通过；
- [x] 无新增 P0 架构、安全、权限、证据、版本或迁移问题，所有声明与真实证据一致。

---

## 14. 禁止事项与停止边界

1. 不得在 M3 正式验收和用户明确下发 M4 前开始实现。
2. 不得新增 OntologyVersion、独立本体数据库、`/ontologies` 或第二套版本/发布权威。
3. 不得建设 RDF/OWL/SPARQL IDE、描述逻辑推理机、任意规则执行或强制图数据库。
4. 不得按同名、翻译、向量相似或 LLM 判断自动合并概念。
5. 不得让后安装 Pack 覆盖先安装 Pack，或让安装自动发布 Schema。
6. 不得执行 Pack 内任意代码、模板脚本、宏、二进制或远程 include。
7. 不得为 Equipment/RCA/客户领域增加核心表、字段或条件分支。
8. 不得修改已发布 SchemaVersion、PackVersion、Release 或历史迁移。
9. 不得将 Schema 合规冒充事实正确、Evidence 或专家确认。
10. 不得把 Mock、内存配置、静态页面、固定 JSON 或 LLM 文本冒充真实功能。
11. 不得自动进入 M5；M4 完成后必须停止并按格式回报。

---

## 15. 建议执行步骤

1. 确认 M3 正式验收、用户下发 M4 和当前 Git/工作区基线；
2. 关闭 M4 编码前精确格式/签名/迁移 DSL/Open Question；
3. 先实现 pure domain 和 canonical contracts/JSON Schema；
4. 实现 additive 数据迁移、仓储、API 和权限/审计；
5. 实现确定性 Pack canonicalization/composition 和影响分析；
6. 实现 DomainPackInstall Workflow Activities、恢复/补偿和对账；
7. 实现真实 Schema Studio/语义模型/Pack UI；
8. 补齐 SDK、事件、文档、fixtures、兼容和安全检查；
9. 执行单元、契约、迁移、Workflow、真实 E2E、故障和安全门禁；
10. 做独立审查与修复回归，更新追踪/状态/报告并停止在 M4。

---

## 16. Codex 最终回报格式

```markdown
# NEXWEAVE M4 执行结果

## 1. 总体结论
- 阶段：通过 / 有条件通过 / 不通过
- 是否满足进入下一阶段条件：是 / 否
- Git 基线：提交哈希 / 未提交及原因

## 2. 实际完成范围
- 按对象、Schema、Pack、Workflow、UI 和非目标逐项说明。

## 3. 新增或修改文件
- 路径、用途、对应需求 ID。

## 4. 领域对象、API、事件、SDK 和 Workflow
- stable key / composition / v1 Stub 兼容 / ADR / 公共契约。

## 5. 测试与验证
- 命令、环境、fixture/checksum、结果、未执行项。

## 6. 数据库与迁移
- migration、up/down/up、M0—M3 兼容性。

## 7. 安全、权限、审计与供应链
- Pack、签名、恶意输入、隔离、SBOM/CVE、Secret/日志。

## 8. 版本、兼容与历史保留
- SchemaVersion/PackVersion/composition/升级/回滚/Release 影响。

## 9. 风险与遗留项
- P0 / P1 / P2。

## 10. 需求追踪更新
- VERIFIED / PARTIAL / 未覆盖。

## 11. 停止声明
已停止在 M4，未自行进入下一 Milestone。
```

---

## 17. 交付判定

M4 成功不以类型数量、界面复杂度或“本体”名词判断，而以“单一 SchemaVersion 权威、稳定语义身份、确定性 Pack 组合、冲突/破坏性变更阻断、历史可复现、声明式安全和真实跨系统证据”是否同时成立判断。
