# ADR-0001: NEXWEAVE 独立产品与 GridCrew API 集成

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 产品负责人、双方架构负责人
- Related: OQ-PROD-001, SPK-008

## Context

NEXWEAVE 生产并发布可信知识；GridCrew 编排数字员工和业务任务。两边都有身份、版本、Evidence、Approval、Connector 与模型治理概念，若合并状态或复制内核会产生权威冲突。

## Decision question

两产品应合并为单体、共享业务数据库，还是保持独立并通过公共契约集成？

## Options

1. 合并为 GridCrew 内部知识模块；
2. 独立部署但共享业务数据库/内部代码；
3. 独立部署、独立状态，通过版本化 API、事件和 SDK 集成。

## Decision

选择 3。GridCrew Skill 绑定固定 NEXWEAVE Release；GridCrew 反馈只进入 Source/Draft/Review 流程。双方可兼容或复用基础服务，但不得共享业务状态权威。

## Consequences

正面：生命周期清晰、独立演进、故障隔离、发布可复现。负面：需要身份映射、双平台审计、契约版本和联调环境。

## Migration risks

共享 Model Gateway/IAM/Evidence 语义若未冻结，可能造成重复服务或错误合并。运行中 GridCrew Task 不得因 NEXWEAVE 新 Release 自动漂移。

## Validation

SPK-008 证明固定 Release、服务身份、越权阻断、幂等重试、发布/废止事件和 correlation ID 对账。
