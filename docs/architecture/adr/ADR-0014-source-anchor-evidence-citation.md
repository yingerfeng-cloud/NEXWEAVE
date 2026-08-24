# ADR-0014: SourceAnchor、Evidence、Claim、Relation 与 Citation 语义

- Status: Accepted
- Date: 2026-08-23
- Approval basis: M0 任务书 + Evidence Native 原则
- Decision owners: 知识架构负责人、后端负责人
- Related: OQ-SOURCE-001, OQ-EVID-001, NXW-EVID-001

## Context

页码、段落、表格、图像 bbox 和字符范围不能由一个不带版本的字符串可靠表示。Claim、Relation、Evidence 和回答 Citation 若混为一表，也无法区分事实表达、知识结构、证据判断和回答引用。

## Decision

1. `SourceAnchor` 是版本化复合定位值，必须绑定 `source_version_id`、原始对象 checksum、定位器版本和一种或多种位置描述。
2. 位置描述允许页码、段落/块 ID、字符范围、表格行列、时间范围、规范化 bbox；每种描述包含坐标系统或单位，禁止使用无上下文数字。
3. Anchor 保存规范化 excerpt 的 hash，可选择保存受权限约束的短摘录；不得复制整份敏感原文。
4. 定位状态为 `VALID`、`STALE`、`UNRESOLVED`、`REVOKED`；重解析只生成新 Anchor 或新版本，不原地改写历史 Release 中的定位。
5. `Claim` 表达可审查的事实主张；`Relation` 表达实体/概念间受 Schema 约束的结构关系；`Evidence` 记录某个 SourceAnchor 对 Claim/Relation 的支持、反对或上下文作用及审核状态；`Citation` 记录一次回答具体引用了哪些已发布 Evidence。
6. 正式 Claim 和因果 Relation 至少有一条有效、可见、已发布 Evidence；模型置信度、检索相似度不能代替 Evidence。
7. Citation 必须固定 `release_id`、`evidence_id`、`source_version_id` 和 `source_anchor_id`，并遵循查询者权限与密级。

## Consequences

解析器需要输出稳定定位器和失效检测；查询层不能直接把检索片段冒充 Citation；撤销源访问时历史记录保留但按策略遮蔽并告警。

## Compatibility and migration

定位器新增可选类型可向后兼容；改变坐标语义或删除字段必须提升 `locator_version`，提供转换器和失效报告。Release 不被就地迁移。

## Validation

M0 JSON Schema 覆盖复合定位、hash、状态和约束；M3/M5/M7 分别验证解析定位、证据绑定和不可变发布引用。
