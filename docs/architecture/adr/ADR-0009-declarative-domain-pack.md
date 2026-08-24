# ADR-0009: Domain Pack 声明式扩展

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构/安全/产品负责人
- Related: SPK-006, OQ-PACK-UI-001

## Context

平台需要支持 RCA 等领域语义而不把行业字段写入核心。可执行插件扩展灵活，但在私有化和高密环境带来任意代码、供应链和兼容风险。

## Decision question

Pack 使用声明式配置、任意代码插件，还是为每个领域分叉平台？

## Options

1. 平台分叉；2. 任意代码插件；3. 声明式、签名、版本化 Pack + 受控公共扩展点。

## Decision

选择 3。Pack 声明 Schema、模板、术语、Prompt、审核、Lint、评测、样例和受限 UI 元数据；R1 禁止执行任意代码。

## Consequences

正面：平台/领域解耦、安全、可检查、可迁移。负面：自定义能力受限，需要兼容规则、迁移 DSL、签名和 Registry。

## Migration risks

破坏性 Schema 或 Pack 升级可能影响草稿，但不能修改历史 Release；卸载不得删除知识。

## Validation

SPK-006 用两个 Pack 和恶意制品验证不改平台代码安装、兼容阻断、签名、回滚和数据保留。
