# Repository Structure

| 路径 | M0 状态 | 后续责任 |
|---|---|---|
| `apps/web` | 基础设施状态页 | M1 起按任务书增加真实 API 驱动页面 |
| `apps/api` | 健康、版本、脱敏诊断 API | 模块化单体 API/应用层；M0 无业务路由 |
| `workers/health` | 确定性 Temporal 健康 Workflow | 业务 Worker 仅在对应 Milestone 建立 |
| `packages/domain` | UUIDv7 与冻结枚举 | 框架无关领域规则 |
| `packages/contracts` | Pydantic canonical source、JSON Schema、OpenAPI | 公共 API/事件/SDK 契约单一来源 |
| `packages/sdk` | 目录边界保留 | 从已提交 OpenAPI/Schema 生成 SDK；M0 不伪造业务方法 |
| `packages/ui` | 目录边界保留 | 共享设计系统 |
| `packages/domain-pack-sdk` | 目录边界保留 | Pack 校验与开发契约 |
| `domain-packs/equipment-rca` | 仅声明式示例边界 | 首发 Pack；不得写入平台核心逻辑 |
| `infra/*` | Compose 边界与全合成 M0 fixture | 后续 Temporal/可观测性/部署资产 |
| `tests/*` | 架构、契约和 fixture 门禁 | 按 Milestone 增加集成、安全、E2E |

M0 只写入工程底座代码、基础迁移和公开契约，不包含知识业务功能、模型调用或客户数据。
