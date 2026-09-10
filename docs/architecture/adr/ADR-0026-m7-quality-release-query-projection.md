# ADR-0026: M7 质量门禁、不可变发布与固定版本查询投影

- Status: Accepted
- Date: 2026-08-31
- Approval basis: 用户正式下发 M7；ADR-0006、0008、0014、0016
- Decision owners: 产品、架构、质量、安全负责人
- Related: NXW-QUALITY-001/002, NXW-RELEASE-001/002, NXW-GRAPH-001/002, NXW-QUERY-001/002

## Context

M7 必须把已审核知识变成可复现 Release，并同时避免把数据库当前行、检索索引或模型输出误当正式知识。质量运行、发布审批、索引重建、灰度/回滚和问答引用需要共享一个固定版本边界。

## Decision

1. `EvaluationSuite` 是版本化问题集与门禁策略；`EvaluationRun` 固定 suite/version、目标、检索配置、Prompt/Model 和逐题结果。Lint 与问题集结果均作为追加式质量事实，阻断项或未通过问题使候选不能发布。
2. `ReleaseCandidate` 在创建时固定显式对象 ID、已发布 SchemaVersion/composition checksum、Pack 输入、Prompt/Model 与索引配置。只允许已审核 Claim、正式 Relation、有效 Evidence 和可发布页面版本进入候选；空间内未决阻断冲突阻止发布。
3. 发布采用 `nexweave.knowledge-release.v2`：Activity 执行可重试验证，Workflow 等待独立 Publisher 的明确批准，再由幂等 Activity 在单一数据库事务中写入不可变 `Release`、`ReleaseItem`、默认 channel pointer、Outbox 和可重建查询投影。候选创建者不得批准自己的 Release。
4. Release manifest 使用规范化 JSON 的 SHA-256；空间内 SemVer 不可复用。Release/ReleaseItem/审批/指针历史/问答/Citation 追加式保存。废止是独立事实；回滚或灰度只以乐观锁原子移动 `ReleasePointer`，绝不修改 Release。
5. R1 查询投影由固定 Release 重建：PostgreSQL 全文检索、pgvector 16 维向量和正式 Relation 表分别实现 Search/Vector/GraphQuery Port。混合检索使用可解释 RRF，返回关键词名次、语义名次与融合分数；向量相似度不表示事实置信度。
6. 每次 Query 只绑定一个 `release_id`。M7 本地可信问答采用证据约束的抽取式合成；没有可见、已接受且 Anchor 为 `VALID` 的 Release Evidence 时必须拒答。Citation 固定 Release、Evidence、SourceVersion、SourceAnchor 和答案，不引用草稿或跨 Release 内容。
7. Graph API 只遍历同一 Release 中的正式 Relation，强制 tenant/space/密级、最大深度和结果上限，支持一跳/多跳、最短路径候选、因果过滤、时间切片及 Evidence 引用。
8. 质量、发布、指针切换/回滚、废止和问答均写审计；发布/指针/废止产生 transactional outbox 事件。M8 订阅这些事件，不在 M7 引入外部 Connector。

## Compatibility and migration

- 新增 `0008_m7`，不修改历史迁移；M0—M6 API 与 v1 Workflow 保持可用。
- M6 `evidence_records` 追加 `relation_id` 并将目标约束扩为 Claim、Relation 或候选 Relation 三选一；历史记录不重写。
- 查询 Provider 是可替换投影，不暴露 PostgreSQL、pgvector 或图引擎查询语言。
- 投影可从 ReleaseItem 和权威对象重建；删除投影不会删除 Release。

## Validation

- 领域/契约：SemVer、manifest checksum、门禁、RRF、拒答、权限与错误分支。
- 数据库：`0001→0008→0007→0008`，不可变 trigger、唯一版本、指针历史和历史 sentinel。
- Workflow：质量 v2 和发布 v2 的重试、审批等待、职责分离、幂等固化与失败无半发布。
- E2E：Source→Compile→Review→Evaluate→Release→Query/Citation；指针切换/回滚不改历史；投影重建后引用一致。

