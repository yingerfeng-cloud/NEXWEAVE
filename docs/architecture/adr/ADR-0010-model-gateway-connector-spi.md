# ADR-0010: 统一 Model Gateway 与 Connector SPI

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构/安全负责人
- Related: SPK-007, OQ-GW-001

## Context

模型、Embedding、外部资料和业务系统具有不同认证、数据出域、错误、配额和审计要求。业务代码直接绑定厂商会破坏安全策略和可替换性。

## Decision question

是否强制所有模型调用经 Model Gateway、所有外部资料/系统经 Connector SPI？

## Options

1. 各模块直连；2. 公共工具库但允许绕过；3. 强制 Gateway/SPI，厂商 Adapter 仅在边界层。

## Decision

选择 3。Model Gateway 统一能力声明、结构化输出、密级、脱敏、预算、超时、审计；Connector 统一凭据引用、水位、字段映射、网络白名单、幂等和回执。

## Consequences

正面：安全、治理、供应商替换和测试统一。负面：边界服务成为关键依赖，需要高可用、缓存/限流和清晰错误模型。

## Migration risks

不得把厂商响应作为领域对象；Connector 不得绕过 SourceVersion。与 GridCrew 先保持公共契约兼容；若复用具体服务，必须另行评审权限、可用性和故障隔离。

## Validation

SPK-007 和 M8 合同测试验证两类 Provider、敏感数据阻断、凭据泄漏、失败重试和审计。
