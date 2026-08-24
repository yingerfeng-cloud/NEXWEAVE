# ADR-004: 所有外部调用经过 Tool Gateway

- 状态：Accepted
- 日期：2026-07-25
- 关联：PRD V2.2 第 10、12 章；开发计划 V2.2 第 2、9 章

## 背景

Agent 不得直接访问客户系统，外部调用需处理权限、风险、幂等、审计和回执。

## 决策

所有外部工具和系统调用必须经过 Tool Gateway，再进入 Connector。

## 理由

统一隔离外部系统风险，保证调用可审计、可重试、可限流、可审批。

## 影响

Skill 只能通过 Tool Gateway 发起外部动作。

## 替代方案

Agent 或 Skill 直接调用客户系统 API。

## 后续约束

任何绕过 Tool Gateway 的外部调用都是架构违规。
