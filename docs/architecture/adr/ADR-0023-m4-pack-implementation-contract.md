# ADR-0023: M4 Pack 实现契约——稳定 key、规范格式、签名、迁移与 UI

- Status: Accepted
- Approval basis: 用户于 2026-08-29 正式下发 M4，并明确要求先完成 M4-0 实现级决策冻结
- Date: 2026-08-29
- Decision owners: 产品/架构/知识工程负责人
- Related: ADR-0009, ADR-0013, ADR-0015, ADR-0022; OQ-SEMANTIC-KEY-001, OQ-PACK-FORMAT-001, OQ-PACK-SIGN-001, OQ-PACK-MIGRATION-001, OQ-PACK-UI-001

## Context

ADR-0022 已决定 SchemaVersion 是唯一有效语义快照，并规定 Pack 必须是可复现、声明式且不可执行的输入。M4 编码前仍需把 stable key、制品字节、签名撤销、迁移和 UI 的实施边界精确化，避免不同 API、Registry、Worker 或 UI 对同一 Pack 得出不同结果。

## Decision

### Stable key v1

`type_key`、`relation_type_key` 与 `property_key` 均使用 `namespace/local-name`，并且必须匹配：

```text
^[a-z][a-z0-9.-]{1,62}/[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$
```

- 仅 ASCII 小写；总长度 4—127；不得包含空白、Unicode、路径分隔以外的 `/`、`..`、`_` 或尾部 `-`。
- `namespace` 是已登记的 DNS-like 发布者命名空间，而不是显示名称或文件路径。Pack 的 `metadata.keyNamespace` 必须完全等于其所有新定义的 key namespace。
- `nexweave.io`、`local.nexweave.io` 与 `test.nexweave.io` 为保留命名空间；前者仅平台信任根可发布，后两者只可用于受控本地/测试制品。空间本地声明只能使用服务端发放的 `local.<tenant-short-id>.<space-short-id>.nexweave.io`，不得伪造 Pack namespace。
- 同一 major 中不得改义、复用或删除已发布 key；显示文本变更使用术语，概念演进使用显式 deprecation/mapping/新 key。

### 制品与规范化 v1alpha1

- Pack 权威源为 UTF-8（无 BOM）的 JSON 文件；M4 Registry/API 不接收 YAML。YAML 只可由未来离线作者工具转换成相同 JSON，不能作为可签名或可安装权威输入。
- 根文件固定为 `manifest.json`，`apiVersion` 固定 `nexweave.io/domain-pack/v1alpha1`，`kind` 固定 `NexweaveDomainPack`。所有清单列出的内容路径为相对 POSIX 路径，且匹配 `^[a-z0-9][a-z0-9._/-]{0,191}$`，不含 `//`、`.`、`..`、绝对路径或符号链接。
- 所有 JSON 值仅允许对象、数组、字符串、布尔和整数；拒绝浮点数、指数、NaN、Infinity 和重复对象键。每个文件最大 256 KiB、目录最多 64 文件、嵌套深度最多 32、制品总量最多 2 MiB。
- `canonicalizationAlgorithm` 固定 `RFC8785-JCS/1`。在上述受限 JSON 子集上，以 RFC 8785 的 UTF-8 canonical JSON 产生内容字节；`sha256:<lowercase-hex>` 为每个内容文件及 Pack descriptor 的 checksum。
- Pack descriptor 是 `manifest.json` 删除 `security.signature.value` 后的 canonical JSON。其 SHA-256 为 `contentChecksum`；签名直接覆盖 descriptor canonical UTF-8 bytes。`metadata.id` 必须匹配 `^[a-z][a-z0-9-]{1,62}-pack$`，版本为无 build metadata 的 SemVer 2.0.0。

### 签名、信任与撤销

- v1alpha1 唯一允许 `security.signature.algorithm = Ed25519`。`keyId` 匹配 `^[A-Za-z0-9._-]{1,128}$`；`value` 是 64-byte detached signature 的无填充 base64url 编码。
- 安装时必须使用租户可见、ACTIVE 的信任根/发布者公钥离线验证 descriptor signature、全部文件 checksum、key namespace ownership、平台/语义契约范围与依赖锁定。无签名、未知 key、错配、过期或已撤销制品一律拒绝。
- 撤销清单为受信任根签发的 JSON `nexweave.io/pack-revocation/v1alpha1`，同样使用 RFC8785-JCS/1 + Ed25519；按精确 `packId/version/contentChecksum` 或 `keyId` 撤销。撤销立即阻断新安装、升级和发布；不会删除历史 PackVersion、SchemaVersion、Release 或审计。M4 不进行网络拉取，撤销清单由受审计的管理员导入。
- 私钥永不进入 Pack、数据库业务行、日志、事件或客户端；数据库只保存公钥、指纹、信任状态、撤销证据摘要与审核元数据。

### 迁移 DSL v1alpha1

- 迁移是 JSON declaration，固定 `apiVersion: nexweave.io/schema-migration/v1alpha1`、`kind: NexweaveSchemaMigration`、`from`/`to` 精确 PackVersion checksum 与有序 `operations`。它只生成兼容性和影响预览；M4 不执行实例数据变换。
- 每个迁移最多 100 个操作、32 KiB canonical bytes，且只允许：`addType`、`addOptionalProperty`、`addRelation`、`addSubtype`、`renameDisplay`、`addTerm`、`deprecate`、`addRelatedMapping`。
- 每个操作必须声明稳定 `operationId`；可逆操作以显式 `rollback` 表达准确逆操作。不可逆或破坏性声明可被记录为预览，但使 SchemaVersion 不能直接发布，直至后续迁移验证和独立批准完成。
- DSL 不含表达式、循环、条件、文件/网络引用、脚本、模板求值或任意数据选择器。删除/改义 key、收紧约束、EXACT mapping、数据重写和回填不属于 M4 DSL。

### 声明式 UI 边界

- `ui` 仅允许 `icon`（受控 token）、`colorToken`、`form` 字段顺序/分组、`list` 列、`semanticModel` 默认视图和只读帮助文本。所有引用只可指向同 Pack 已声明 stable key。
- 禁止 HTML、Markdown/富文本渲染指令、JavaScript/CSS、iframe、URL、远程资产、自定义组件、动态表达式、事件处理器与模板执行。服务端忽略未知字段并将其报告为 Pack validation error，而非降级执行。
- UI 声明只影响展示，不能赋予权限、改变审核/发布、绕过 schema 校验或改变 API 行为；平台 UI 必须提供所有关键状态的安全默认呈现。

## Consequences

M4 以单一可审计 JSON 制品格式换取确定的跨语言签名和组合行为；YAML 作者体验、在线透明日志、私有 Pack 发布和 richer UI extensions 留待有独立 ADR 的后续阶段。任何改变 key regex、canonicalization、signature/撤销语义、DSL 操作或 UI 执行能力的提案必须新增 ADR 并提供兼容窗口。
