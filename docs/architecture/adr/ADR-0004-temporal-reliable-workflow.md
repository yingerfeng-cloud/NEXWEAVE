# ADR-0004: Temporal 作为可靠知识工作流

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构负责人
- Related: OQ-EXEC-001, SPK-001, NXW-ARCH-002

## Context

解析、编译、审核、评测、发布、Pack 安装和反馈包含长等待、重试、人工 Signal、补偿与恢复。普通后台线程、数据库轮询或 Agent Runtime 无法提供统一可靠历史。

## Decision question

是否以 Temporal 为长任务唯一执行权威，数据库仅保存业务事实和查询投影？

## Options

1. Temporal；2. Celery/消息队列 + 自建状态机；3. 数据库轮询；4. Agent Runtime 执行生命周期。

## Decision

选择 1。Workflow 保持确定性，外部 I/O 全部在幂等 Activity；业务 ID 与 Workflow ID 稳定映射。SPK-001 继续验证升级、长等待和灾难恢复风险。

## Consequences

正面：durable timer、Replay、Signal/Update、重试和恢复统一。负面：运维/升级复杂、开发者需理解确定性和版本化、投影对账仍需建设。

## Migration risks

DB 若继续推进状态会形成双状态机；Workflow 代码升级不兼容会阻断 Replay；超大历史需 Continue-As-New 策略。

## Validation

SPK-001 覆盖 Replay、时间跳跃、Worker 重启、取消、补偿、版本升级、长等待和投影修复。
