# Domain Pack Specification Baseline

> 状态：ADR-0022 冻结 M4 语义组合规则，ADR-0023 已冻结 v1alpha1 stable key、JSON canonical format、签名/撤销、迁移 DSL 与 UI 边界。Domain Pack 是数据/声明包，不是可执行插件。

## 1. 包结构

```text
manifest.yaml
schema/
  entities.yaml
  properties.yaml
  hierarchy.yaml
  relations.yaml
  mappings.yaml
templates/
terminology/
prompts/
review/
lint/
evaluation/
samples/
migrations/
ui/
```

## 2. Manifest 最小字段

| 字段 | 语义 |
|---|---|
| `apiVersion` | Pack 契约 major/minor |
| `kind` | 固定 `NexweaveDomainPack` |
| `metadata.id` | `<domain-id>-pack`，稳定且全局可区分 |
| `metadata.version` | 不可变 Pack 版本，SemVer 候选 |
| `metadata.publisher` | 发布者 ID/名称/信任域 |
| `metadata.description` | 非执行描述 |
| `compatibility.platform` | 支持的平台版本范围 |
| `compatibility.dependencies` | Pack ID/版本依赖 |
| `compatibility.semanticContract` | 支持的 NEXWEAVE 语义契约版本范围 |
| `content` | 各声明文件路径与 checksum |
| `security.signature` | 签名算法、key ID、签名引用 |
| `permissions` | 所需平台能力；默认无网络/文件/模型任意访问 |
| `migrations` | 声明式迁移、前置版本和可回滚性 |

## 3. 内容规范

- EntityType：命名空间化稳定 `type_key`、显示信息和声明来源；同名不自动复用。
- PropertyDefinition：稳定 `property_key`、所属 type key、字段类型、唯一键、必填、枚举/引用、基数、默认值和合并策略。
- TypeHierarchyEdge：child/parent type key；组合后必须形成无环图，多父继承约束不得冲突。
- RelationType：稳定 `relation_type_key`、起止 type key、方向、基数、逆关系候选、是否因果、是否要求 Evidence、时效。
- ConceptMapping：source/target stable key、`EXACT/BROADER/NARROWER/RELATED`、来源和审核要求；不物理覆盖来源定义。
- PageTemplate：标题、元数据、章节、自动生成区、人工保护区、引用展示。
- Terminology：绑定稳定 type/relation key 的标准术语、同义词、缩写、语言、适用范围和歧义规则；与实例 EntityAlias 分离。
- Prompt：任务用途、结构化输出契约、版本、允许模型能力和安全限制。
- Review：风险分级、角色、职责分离、批量策略和超时。
- Lint：声明式条件、严重度、阻断性、修复提示。
- Evaluation：可回答、不可回答、反事实、冲突、多来源和证据不足问题。
- Samples：虚构/脱敏演示数据，包含许可证/授权和期望结果。
- UI：R1 只建议声明式图标、颜色、表单/视图布局；自定义可执行组件待决策。

## 4. 生命周期

1. Build：生成规范化清单和内容 checksum；
2. Validate：Schema、安全、稳定 key、依赖 DAG、语义引用、兼容、迁移和样例测试；
3. Sign/Publish：不可变制品和签名；
4. Install：将依赖范围解析为精确 PackVersion/checksum，确定性组合并生成 DRAFT SchemaVersion 与 SchemaCompositionReport；安装成功不自动发布 Schema；
5. Upgrade：显式兼容检查和迁移，不原地改已发布 Release；
6. Disable/Uninstall：停止新使用，不删除既有知识；
7. Rollback：恢复先前安装/配置指针并保留审计。

## 5. 安全原则

- Pack 不得包含或执行任意 Python、JavaScript、Java、Shell、二进制或宏。
- Prompt、模板和样例均视为不可信输入，需限制大小、引用和模板能力。
- 禁止绝对路径、路径穿越、远程 include、未声明网络访问和凭据。
- 内容需 checksum；企业分发需签名、信任根、撤销和 SBOM/许可证记录。
- Pack 不得修改平台核心表、绕过权限/审计/Evidence/Release 或直接调用模型/Connector。

## 6. 声明式迁移

允许的候选操作：新增可选字段/类型/关系/模板/规则，新增不收紧既有约束的子类型，重命名显示文案，声明术语，弃用定义，增加 RELATED mapping，受控数据映射。删除或改义 stable key、新增必填、缩窄类型/枚举/基数、改变唯一键/父类型/关系端点/合并策略/Evidence 要求、增加或改变 EXACT mapping 等默认为破坏性变更，必须阻断直接发布并生成影响报告、迁移计划、测试和人工批准。

## 7. 确定性组合与冲突

组合顺序固定为平台公共契约约束、精确 PackVersion 依赖 DAG、空间本地声明扩展，最终生成不可变 SchemaVersion。规则如下：

1. 依赖图必须无环并解析为唯一、精确版本；相同输入不得因安装时间或数据库顺序产生不同结果；
2. 同一 stable key 的规范定义完全一致时可复用；兼容扩展可增加可选术语、属性或子类型；
3. 重复 key 且约束不一致、层级/依赖循环、继承冲突、悬空端点、歧义 EXACT mapping 和不兼容版本范围必须形成阻断冲突；
4. 禁止“后安装覆盖先安装”；覆盖、映射、取代和弃用都必须显式声明；
5. 空间扩展不修改 Pack 制品，只参与生成新的 SchemaVersion；
6. 组合报告固化输入、规范化算法版本、冲突、影响范围和 composition checksum；相同输入必须产生相同 checksum；
7. 升级重新组合并创建新 SchemaVersion；禁用/卸载/回滚不删除历史 Schema、知识、报告或 Release。

## 8. Equipment RCA Pack 最小示例

```yaml
apiVersion: nexweave.io/domain-pack/v1alpha1
kind: NexweaveDomainPack
metadata:
  id: equipment-rca-pack
  version: 0.1.0
  publisher: nexweave-official
  description: "脱敏的设备 RCA 知识建模示例；不提供自动诊断或处置。"
compatibility:
  platform: ">=1.0.0 <2.0.0"
  dependencies: []
  semanticContract: ">=1.0.0 <2.0.0"
content:
  entities:
    path: schema/entities.yaml
    sha256: "<build-time-checksum>"
  properties:
    path: schema/properties.yaml
    sha256: "<build-time-checksum>"
  relations:
    path: schema/relations.yaml
    sha256: "<build-time-checksum>"
  hierarchy:
    path: schema/hierarchy.yaml
    sha256: "<build-time-checksum>"
  mappings:
    path: schema/mappings.yaml
    sha256: "<build-time-checksum>"
  templates:
    path: templates/index.yaml
    sha256: "<build-time-checksum>"
  terminology:
    path: terminology/zh-CN.yaml
    sha256: "<build-time-checksum>"
  prompts:
    path: prompts/index.yaml
    sha256: "<build-time-checksum>"
  review:
    path: review/policy.yaml
    sha256: "<build-time-checksum>"
  lint:
    path: lint/rules.yaml
    sha256: "<build-time-checksum>"
  evaluation:
    path: evaluation/suite.yaml
    sha256: "<build-time-checksum>"
security:
  executableContent: false
  signature:
    algorithm: "<approved-algorithm>"
    keyId: "<approved-key-id>"
    value: "<detached-signature>"
```

示例实体候选：Equipment、Component、Symptom、AlarmEvent、FailureMode、DirectCause、RootCause、Mechanism、VerificationMethod、ExclusionCondition、CorrectiveAction、HistoricalCase、DataIndicator、ExpertRule。示例关系和字段只存在于 Pack，不成为平台核心表或 Python 根包。

## 9. 已冻结与待 M4 实现决策

已由 ADR-0022 冻结：SchemaVersion 单一语义权威、stable key、类型层级、术语/映射、确定性 Pack 组合、禁止静默覆盖、兼容分类、安装不自动发布和历史不删除。

ADR-0023 已冻结 JSON-only `v1alpha1`、`RFC8785-JCS/1`、Ed25519/撤销清单、stable key regex、preview-only migration DSL 与非执行 UI。Registry transport、私有发布治理和 Prompt 细则仍按现有安全基线执行；GridCrew Skill 映射在 M8 前联合冻结，不得在 M4 静默决定。
