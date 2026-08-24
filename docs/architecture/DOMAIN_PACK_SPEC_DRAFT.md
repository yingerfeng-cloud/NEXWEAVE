# Domain Pack Specification Draft

> 状态：M-1 Draft；供 M0/M4 冻结。Domain Pack 是数据/声明包，不是可执行插件。

## 1. 包结构

```text
manifest.yaml
schema/
  entities.yaml
  relations.yaml
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
| `content` | 各声明文件路径与 checksum |
| `security.signature` | 签名算法、key ID、签名引用 |
| `permissions` | 所需平台能力；默认无网络/文件/模型任意访问 |
| `migrations` | 声明式迁移、前置版本和可回滚性 |

## 3. 内容规范

- EntityType：属性、字段类型、唯一键、必填、枚举、合并策略、页面模板。
- RelationType：起止类型、方向、基数、是否因果、是否要求 Evidence、时效。
- PageTemplate：标题、元数据、章节、自动生成区、人工保护区、引用展示。
- Terminology：标准术语、同义词、缩写、语言、适用范围和歧义规则。
- Prompt：任务用途、结构化输出契约、版本、允许模型能力和安全限制。
- Review：风险分级、角色、职责分离、批量策略和超时。
- Lint：声明式条件、严重度、阻断性、修复提示。
- Evaluation：可回答、不可回答、反事实、冲突、多来源和证据不足问题。
- Samples：虚构/脱敏演示数据，包含许可证/授权和期望结果。
- UI：R1 只建议声明式图标、颜色、表单/视图布局；自定义可执行组件待决策。

## 4. 生命周期

1. Build：生成规范化清单和内容 checksum；
2. Validate：Schema、安全、依赖、兼容、迁移和样例测试；
3. Sign/Publish：不可变制品和签名；
4. Install：在测试空间预览影响，经批准后生成平台 Schema/配置版本；
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

允许的候选操作：新增可选字段/类型/关系/模板/规则，重命名显示文案，声明别名，弃用定义，受控数据映射。删除、缩窄类型、改变唯一键、改变关系端点、取消 Evidence 要求等为破坏性变更，必须阻断直接发布并生成影响报告和人工批准的迁移计划。

## 7. Equipment RCA Pack 最小示例

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
content:
  entities:
    path: schema/entities.yaml
    sha256: "<build-time-checksum>"
  relations:
    path: schema/relations.yaml
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

## 8. 待 M0/M4 决策

规范格式 JSON/YAML 单一来源、SemVer 兼容规则、签名/撤销、Registry、Prompt 安全、声明式 UI 能力、迁移 DSL、跨 Pack 依赖、企业私有发布和 GridCrew Skill 映射。
