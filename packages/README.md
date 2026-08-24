# Shared Packages

M0 在 `domain` 中实现纯 UUIDv7/状态词汇，在 `contracts` 中实现公共 Pydantic canonical source 及提交的 JSON Schema/OpenAPI 快照。`sdk`、`ui` 和 `domain-pack-sdk` 继续保留边界，必须等对应公共契约和 Milestone 再生成或实现，不能用空方法冒充能力。

`domain` 与 `contracts` 不得依赖 Web 框架、数据库、Temporal、存储或厂商 SDK；该规则由架构测试持续阻断。
