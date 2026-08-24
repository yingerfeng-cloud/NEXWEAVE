# ADR-0002: Monorepo、模块化单体与独立 Worker

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构负责人、研发负责人
- Related: NXW-ARCH-001, SPK-009

## Context

R1 同时包含 Web、API、领域契约、可靠 Workflow、Parser/Compile/Release Worker、SDK 和 Pack。过早微服务化会放大部署、契约和一致性成本，但长任务需要独立扩缩与故障隔离。

## Decision question

R1 采用多仓微服务、单体，还是 Monorepo 中的模块化单体 API + 独立 Worker？

## Options

1. 多仓微服务；2. 单进程单体；3. Monorepo、模块化单体 API、独立 Worker 和公共 packages。

## Decision

选择 3。逻辑模块和 Port 先固定，Parser/Compile/Evaluate/Release Worker 独立部署；规模增长时按契约拆分。

## Consequences

正面：原子变更、契约复用、较低运维成本、可独立扩展长任务。负面：需严格架构测试防止跨模块直连；CI 范围和包版本管理更复杂。

## Migration risks

若模块边界只存在文档中，单体会演化为耦合内核；若 Worker 共享内部 ORM，未来拆分困难。

## Validation

M0 建立依赖规则、架构测试、公共契约生成、最小 API/Web/Worker 健康链路和独立部署拓扑。
