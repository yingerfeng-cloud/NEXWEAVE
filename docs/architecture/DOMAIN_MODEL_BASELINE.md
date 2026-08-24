# Domain Model Baseline

> 状态：M-1 概念基线；对象字段、状态机和 ID 方案须在 M0 通过 ADR/契约冻结。  
> 通用字段：除明确的全局配置外，业务对象预留 `id`、`tenant_id`、`space_id`、`status`、`version/etag`、`created_by`、`updated_by`、`created_at`、`updated_at`。

## 1. 身份与空间

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| Tenant | 安全与数据隔离顶层，`tenant_id` | 平台级；配置版本 | ACTIVE/SUSPENDED/ARCHIVED | Organization、User、Space | DB | AI 禁止；管理员批准 |
| Organization | 租户内组织树，`organization_id` | tenant；乐观锁 | ACTIVE/ARCHIVED | User、SpaceMember | DB | AI 禁止；管理员维护 |
| User | 人员身份映射，`user_id` | tenant；外部 subject 可变映射 | INVITED/ACTIVE/SUSPENDED/ARCHIVED | Membership、ReviewAction、Approval | DB + IdP 身份事实 | AI 禁止；管理员维护 |
| ServiceIdentity | 系统/应用调用身份，`service_identity_id` | tenant；凭据只存引用且轮换 | ACTIVE/SUSPENDED/REVOKED | Connector、GridCrew 调用 | DB + Secret Provider | AI 禁止；安全审批 |
| KnowledgeSpace | 知识治理与隔离单元，`space_id` | tenant；配置不可静默覆盖 | INITIALIZING/BUILDING/PUBLISHED/FROZEN/ARCHIVED | 所有空间知识对象 | DB | AI 禁止创建正式空间；管理员批准 |
| SpaceMember | 用户/服务身份与空间授权关系，`space_member_id` | tenant/space；策略版本 | ACTIVE/REVOKED | User/ServiceIdentity、Role/Policy | DB | AI 禁止；管理员批准 |

## 2. 原始资料与解析

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| SourceDocument | 逻辑资料及替代链，`source_document_id` | tenant/space；聚合多个版本 | ACTIVE/INVALID/ARCHIVED | SourceVersion、Connector | DB | AI 可建议元数据；人工确认 |
| SourceVersion | 不可变原始版本，`source_version_id` | tenant/space；同一幂等请求 + checksum 唯一；相同字节不跨业务对象静默合并 | STORED/PARSING/PARTIAL/PARSED/FAILED/SUPERSEDED | Object key、ParseJob、Evidence | DB 元数据 + 对象存储字节 | AI 不得修改；上传/失效受权；上传会话与扫描执行状态不扩展聚合状态 |
| ParseJob | 对一个 SourceVersion 的解析执行，`parse_job_id` | tenant/space；每次解析新记录 | CREATED/QUEUED/RUNNING/PARTIAL_FAILED/FAILED/SUCCEEDED/CANCELED | SourceVersion、Segment、Workflow | Temporal 执行 + DB 投影/结果 | AI 可参与 OCR 后处理；结果需质量检查 |
| DocumentSegment | 版本化解析块，`segment_id` | tenant/space；绑定 parser/config version | VALID/INVALIDATED | SourceVersion、SourceAnchor | DB/对象存储衍生结果 | AI 可生成派生标签；非正式知识 |
| SourceAnchor | Evidence 定位值对象，`source_anchor_id` 或 Evidence 内嵌版本对象 | tenant/space；绑定 SourceVersion 与 anchor schema version | VALID/STALE/INVALID/RELOCATED | Segment、Evidence | DB | AI 可提出；发布前必须可验证 |

## 3. Schema 与模板

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| SchemaDefinition | Schema 稳定身份，`schema_definition_id` | tenant/space；多版本 | ACTIVE/ARCHIVED | SchemaVersion | DB | AI 可建议草稿；人工维护 |
| SchemaVersion | 不可覆盖的 Schema 快照，`schema_version_id` | tenant/space；显式版本 | DRAFT/TESTING/PUBLISHED/DEPRECATED | 类型、模板、规则、Release | DB | AI 可辅助；发布需批准 |
| EntityType | 实体类型定义，`entity_type_id` | SchemaVersion 内固定 | DRAFT/PUBLISHED/DEPRECATED | Entity、PageTemplate | DB | AI 可建议；Schema 审核 |
| RelationType | 关系类型与因果/证据约束，`relation_type_id` | SchemaVersion 内固定 | DRAFT/PUBLISHED/DEPRECATED | Relation、EntityType | DB | AI 可建议；Schema 审核 |
| PageTemplate | 页面结构和保护区，`page_template_id` | SchemaVersion 内固定 | DRAFT/PUBLISHED/DEPRECATED | WikiPageVersion | DB | AI 可建议；人工发布 |
| LintRule | 声明式质量规则，`lint_rule_id` | SchemaVersion/Pack 版本 | DRAFT/ENABLED/DISABLED/DEPRECATED | EvaluationRun、Release gate | DB | AI 可建议；管理员批准 |

## 4. 知识对象

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| WikiPage | 页面稳定身份，`wiki_page_id` | tenant/space；指向版本 | DRAFT/IN_REVIEW/APPROVED/RELEASED/DEPRECATED | WikiPageVersion、Entity | DB | AI 可创建草稿；发布需审核 |
| WikiPageVersion | 不可覆盖页面内容，`wiki_page_version_id` | tenant/space；序号/etag | AI_DRAFT/EDITING/PENDING_REVIEW/APPROVED/REJECTED/RELEASED/DEPRECATED | Template、Claim、Evidence、ReleaseItem | DB + 可交换 Markdown | AI 可创建；正式需人审 |
| Entity | 类型化真实世界概念，`entity_id` | tenant/space；版本/合并链 | CANDIDATE/ACTIVE/MERGED/DEPRECATED | EntityType、Alias、Relation、Page | DB | AI 可创建候选；消歧/正式需审核策略 |
| EntityAlias | 实体别名/术语映射，`entity_alias_id` | tenant/space；有效期 | CANDIDATE/ACTIVE/REJECTED/DEPRECATED | Entity、Terminology | DB | AI 可建议；歧义项人审 |
| Relation | 实体间类型化边，`relation_id` | tenant/space；不可静默覆盖 | CANDIDATE/PENDING_REVIEW/APPROVED/REJECTED/RELEASED/DEPRECATED | Entity、RelationType、Evidence | DB | AI 可创建候选；因果/正式需人审与 Evidence |
| Claim | 带 Scope/时效/可信等级的可争议主张，`claim_id` | tenant/space；新语义形成新版本/替代关系 | CANDIDATE/PENDING_REVIEW/APPROVED/REJECTED/RELEASED/DEPRECATED | Subject/Predicate/Object、Evidence、Conflict | DB | AI 可创建候选；正式需 Evidence 与人审 |
| Evidence | 对 Claim/Relation 的可验证支持或反对证据，`evidence_id` | tenant/space；绑定不可变 SourceVersion/Anchor | CANDIDATE/VALID/STALE/REJECTED/RELEASED | SourceVersion、Anchor、Claim/Relation | DB + Raw 引用 | AI 可提出；正式需定位校验/审核 |
| Conflict | 不兼容知识的治理对象，`conflict_id` | tenant/space；保留双方版本 | OPEN/ASSIGNED/IN_REVIEW/RESOLVED/UNRESOLVED/EXPIRED/REOPENED | Claim/Relation/Page、Evidence、Review | DB | AI/规则可创建；解决需人审 |

## 5. 编译、审核与质量

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| CompileJob | 编译业务任务，`compile_job_id` | tenant/space；锁定输入/配置版本 | CREATED/QUEUED/RUNNING/PAUSED/PARTIAL_FAILED/FAILED/SUCCEEDED/CANCELED | SourceVersion、SchemaVersion、Prompt、Model、Workflow | Temporal 执行 + DB 投影/结果 | 系统创建；用户授权启动 |
| CompileStep | 可审计步骤结果，`compile_step_id` | tenant/space；重复执行保留 attempt | PENDING/RUNNING/RETRYING/FAILED/SUCCEEDED/SKIPPED | CompileJob、输入输出对象 | DB 结果 + Workflow 执行 | AI 可执行抽取；非正式知识 |
| ReviewTask | 人工审核业务任务，`review_task_id` | tenant/space；锁定被审版本 | CREATED/ASSIGNED/CLAIMED/WAITING_INPUT/APPROVED/REJECTED/CANCELED/EXPIRED | ReviewAction、Approval、Workflow | Temporal 执行 + DB 任务/结果 | 系统创建；人工处理 |
| ReviewAction | 不可变审核动作，`review_action_id` | tenant/space；追加式 | SUBMITTED | ReviewTask、actor、diff、reason | DB append-only | AI 禁止冒充；人工动作 |
| Approval | 对高风险动作的授权事实，`approval_id` | tenant/space；追加式、不可覆盖 | REQUESTED/APPROVED/REJECTED/EXPIRED/REVOKED | ReviewTask、Release、actor | DB | AI 禁止；有权人员批准 |
| EvaluationSuite | 版本化规则和问题集，`evaluation_suite_id` | tenant/space 或 Pack；多版本 | DRAFT/ACTIVE/DEPRECATED | EvaluationRun、Pack | DB | AI 可建议；领域/质量负责人批准 |
| EvaluationRun | 对固定输入和策略的评测，`evaluation_run_id` | tenant/space；锁定 suite/model/prompt/release | CREATED/QUEUED/RUNNING/FAILED/SUCCEEDED/CANCELED | Suite、ReleaseCandidate、结果 | Temporal 执行 + DB 结果 | 自动执行；门禁阈值人工批准 |

## 6. 发布与查询

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| ReleaseCandidate | 待验证发布集合，`release_candidate_id` | tenant/space；锁定候选对象版本 | DRAFT/VALIDATING/PENDING_APPROVAL/APPROVED/REJECTED/DEPLOYING | ReleaseItem draft、Evaluation、Approval | DB + Workflow | 系统可生成；发布需批准 |
| Release | 不可变正式知识快照，`release_id` | tenant/space；显式版本 | RELEASED/ROLLED_BACK/DEPRECATED | ReleaseItem、Schema、索引配置 | DB immutable manifest + 对象存储快照 | AI 禁止直接发布；人工批准 |
| ReleaseItem | Release 中的固定对象引用/快照，`release_item_id` | tenant/space/release；不可变 | RELEASED/DEPRECATED_WITH_RELEASE | Page/Entity/Relation/Claim/Evidence versions | DB/对象存储 | 系统固化；随 Release 审批 |
| ReleasePointer | 当前服务版本指针，`release_pointer_id` | tenant/space/channel；乐观锁 | ACTIVE | Release | DB | AI 禁止；授权发布/回滚动作 |
| QuerySession | 查询上下文，`query_session_id` | tenant/space；锁定 Release/权限策略 | ACTIVE/CLOSED/EXPIRED | QueryAnswer | DB | 用户/服务发起；审计 |
| QueryAnswer | 可复现回答，`query_answer_id` | tenant/space；不可覆盖 | COMPLETED/REFUSED/FAILED | QuerySession、Release、Citation、Model/Prompt | DB | AI 可生成；必须受证据/安全策略约束 |
| Citation | 回答中对 Release 知识和 Raw 证据的引用，`citation_id` | tenant/space；绑定 Answer/Release/Evidence | VALID/INVALID | QueryAnswer、Evidence、SourceAnchor | DB | 系统生成；返回前锚点验证 |

## 7. Pack、集成与配置

| 对象 | 含义 / ID | 归属与版本 | 生命周期 | 关键关系 | 权威源 | AI / 人审 |
|---|---|---|---|---|---|---|
| DomainPack | Pack 稳定身份，`domain_pack_id` | 发布者/tenant；多版本 | ACTIVE/DEPRECATED | DomainPackVersion | DB/Registry metadata | AI 可辅助创建草稿；发布需签名/审核 |
| DomainPackVersion | 不可变声明包，`domain_pack_version_id` | Pack；SemVer 候选 | DRAFT/VALIDATED/PUBLISHED/REVOKED/DEPRECATED | Schema、Template、Rule、Suite | Registry/Object storage | AI 可生成草稿；发布需审核 |
| Installation | 空间内 Pack 安装事实，`installation_id` | tenant/space；记录版本历史 | PLANNED/INSTALLING/ACTIVE/FAILED/ROLLING_BACK/ROLLED_BACK/DISABLED | PackVersion、SchemaVersion、Workflow | DB + Workflow | 系统执行；管理员批准 |
| Connector | 连接器定义/实例聚合，`connector_id` | tenant/space；配置版本 | DRAFT/ACTIVE/PAUSED/FAILED/REVOKED/ARCHIVED | CredentialRef、SyncRun、Source | DB；凭据在 Secret Provider | AI 禁止配置凭据；管理员批准 |
| ConnectorSyncRun | 同步执行，`connector_sync_run_id` | tenant/space；记录 watermark | CREATED/RUNNING/PARTIAL_FAILED/FAILED/SUCCEEDED/CANCELED | Connector、SourceVersion、Workflow | Temporal + DB 结果 | 系统执行；授权策略 |
| ModelProfile | 模型能力、路由和安全策略，`model_profile_id` | tenant/space 或平台；版本化 | DRAFT/ACTIVE/DISABLED/DEPRECATED | PromptVersion、Compile/Query | DB；密钥在 Secret Provider | AI 禁止启用；管理员批准 |
| PromptVersion | 不可覆盖 Prompt/结构化输出契约，`prompt_version_id` | tenant/space/Pack；版本化 | DRAFT/TESTING/ACTIVE/DEPRECATED | CompileJob、QueryAnswer、Evaluation | DB/Object storage | AI 可生成草稿；启用需评测/批准 |
| AuditLog | 关键安全与业务动作事实，`audit_log_id` | tenant/space；append-only | RECORDED/SEALED | actor、target、correlation | DB/审计存储 | AI 禁止伪造或修改；系统记录 |
| OutboxEvent | 待发布业务事件事实，`outbox_event_id` | tenant/space；append-only | PENDING/PUBLISHED/FAILED/DEAD_LETTER | aggregate、Event envelope | DB | 系统生成；不可由客户端伪造 |

## 8. 语义边界

- `SourceVersion` 是原始资料版本；`Evidence` 是对某个知识主张的可验证引用；`Citation` 是回答中展示和记录的 Evidence/Release 引用。
- `Relation` 是类型化实体边；`Claim` 是有 Scope、时效、可信等级、正反证据和审核语义的可争议陈述。因果 Relation 可由 Claim/Evidence 支撑，但两者不合并。
- `ReviewTask` 管理人工工作；`ReviewAction` 是不可变动作；`Approval` 是对受控决策的授权事实；`Release` 是批准后生成的不可变正式快照。
- NEXWEAVE 的知识 Evidence 与 GridCrew 的执行 Evidence 可互相引用，但不共享主键、数据库或生命周期。

## 9. 状态权威原则

- Temporal 推进长流程；DB 不自行轮询推进状态。
- DB 保存业务对象、人工决策、执行结果和查询投影；Workflow 历史不取代 Release/Approval 业务事实。
- 前端、缓存、Markdown、Git、搜索、向量和图投影都不是生产业务唯一权威源。
- 所有跨源投影必须可对账、修复，并由固定 Release 重建。
