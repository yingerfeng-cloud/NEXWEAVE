# ADR-0015: 公共契约、错误、权限与数据密级

- Status: Accepted
- Date: 2026-08-23
- Approval basis: M0 任务书 + 服务端安全边界
- Decision owners: 架构负责人、安全负责人
- Related: OQ-SEC-001, NXW-SEC-001, NXW-API-001

## Context

API、事件、SDK 和 Worker 若使用不同错误、身份和密级表达，集成方会依赖内部实现，前端也可能错误承担授权职责。

## Decision

1. 公共 HTTP API 使用 `/api/v1`；契约以 OpenAPI 3.1 和 JSON Schema Draft 2020-12 为权威，生成代码不得反向覆盖契约。
2. HTTP 错误使用 `application/problem+json`，稳定字段为 `type/title/status/detail/instance/code/trace_id/errors`；调用方只依赖稳定 `code`，不解析 detail。
3. 资源权限采用服务端 RBAC + ABAC：角色授予动作集合，策略再按 tenant、space、密级、对象状态和职责分离收窄。默认拒绝。
4. 基础角色为 `platform_admin`、`tenant_admin`、`space_admin`、`knowledge_engineer`、`reviewer`、`publisher`、`consumer`、`auditor`、`service`；角色不是数据库超级权限。
5. 数据密级为 `PUBLIC`、`INTERNAL`、`CONFIDENTIAL`、`HIGHLY_RESTRICTED`。策略决定可见、可导出和模型路由；`HIGHLY_RESTRICTED` 禁止外部托管模型，其他级别也必须遵守部署策略。
6. 身份来自验证后的 OIDC token 或服务凭据；租户/空间声明与资源事实共同校验。浏览器参数和未经验证的 header 不能授予权限。
7. 所有写操作具有审计事件；错误、日志、指标和 trace 不记录密钥、token 或未脱敏原文。
8. 兼容变更可在同一 major 版本追加可选字段；删除/改义/收紧枚举需新 major 或明确弃用窗口和转换策略。

## Consequences

应用层必须统一错误映射、授权接口和审计端口；前端只展示服务端判定结果。合同测试必须阻断错误码漂移和敏感字段进入响应。

## Validation

M0 校验 Problem、事件和通用元数据 schema；后续每个资源接口增加权限矩阵、跨租户、密级和错误合同测试。
