# ADR-0016: Release 版本、幂等、事件与状态投影

- Status: Accepted
- Date: 2026-08-23
- Approval basis: M0 任务书 + Raw/Draft/Release 分离原则
- Decision owners: 产品负责人、架构负责人、质量负责人
- Related: OQ-QUERY-001, OQ-RELEASE-001, NXW-RELEASE-001

## Context

发布、查询、事件重试和 Temporal 状态投影若没有统一版本与幂等规则，会出现重复副作用、当前版本漂移和 Workflow/数据库双状态源。

## Decision

1. Release 在 `tenant_id + space_id` 内使用 SemVer；版本不可复用。每个 Release 拥有不可变 manifest checksum，列出精确对象版本、Schema、Pack、Prompt/Model profile 与投影配置。
2. `draft`、`review`、`release` 是隔离层而非一个可随意覆盖的状态字段。修正产生新对象版本和新 Release。
3. R1 每次 Query 必须显式或由受控 channel pointer 解析到一个固定 `release_id`；一次回答不得混用多个 Release。
4. `stable/canary` 等 channel pointer 是独立、审计的可变资源；灰度与回滚只原子移动指针，不修改 Release。
5. 所有产生副作用的公共命令接收 `Idempotency-Key`。服务端以 tenant、actor、operation、key 和规范化 request hash 建立唯一记录；相同 key/相同 hash 返回原结果，相同 key/不同 hash 返回 `IDEMPOTENCY_KEY_REUSED`。
6. 事件采用 transactional outbox；事件 ID 全局唯一，含 aggregate ID/version、occurred_at、trace/correlation/causation ID、tenant/space 和 schema version。消费者按 event ID 或业务幂等键去重。
7. Temporal Workflow ID 由稳定业务 ID/操作类型推导。Temporal 是执行状态权威；数据库仅存业务结果与可修复查询投影，不能独立推进 Workflow。
8. 投影必须包含最后处理事件/Workflow 版本，可通过 outbox、Temporal history 和权威业务状态对账重建。

## Consequences

发布与 Query 不能依赖“当前行”；重试不会重复创建版本或发送外部回执；状态页面必须明确展示投影延迟而非伪装成执行真相。

## Compatibility and migration

Release manifest、事件 envelope 和幂等语义改变必须版本化。历史 manifest/event 不重写；消费者至少支持当前和前一 schema major 的迁移窗口，具体窗口在对外集成前冻结。

## Validation

M0 契约测试覆盖 event envelope 与 idempotency；M2/M7 分别验证 Workflow 重试/投影修复和发布回滚/回答复现。
