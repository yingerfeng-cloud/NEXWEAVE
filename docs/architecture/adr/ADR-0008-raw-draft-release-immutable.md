# ADR-0008: Raw/Draft/Release 分层与不可变 Release

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 产品/架构/质量负责人
- Related: NXW-RELEASE-001, NXW-KQ-001

## Context

企业知识必须区分原始事实、AI/人工候选和正式可消费版本。静默覆盖会破坏引用、审核责任和历史回答复现。

## Decision question

如何定义三层状态和发布/回滚语义？

## Options

1. 页面就地更新并打标签；2. 草稿/正式逻辑标志；3. 不可变 SourceVersion、版本化 Draft、不可变 Release manifest 与服务指针。

## Decision

选择 3。业务查询默认绑定固定 Release；Release 固化对象版本、Schema、Prompt/Model 和索引配置。修正产生新 Release；回滚仅切换指针。

## Consequences

正面：可追溯、可复现、可审计、可重建。负面：存储增长、版本/指针/索引生命周期和垃圾回收更复杂。

## Migration risks

不得把数据库当前行、搜索索引别名或 Git tag 单独当 Release。Source 失效后历史 Release 的可见/告警策略需明确。

## Validation

M0 契约测试；M7 验证发布失败、指针切换、历史查询、索引重建、回答复现和权限隔离。
