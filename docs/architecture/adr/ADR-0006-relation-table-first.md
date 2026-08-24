# ADR-0006: 关系表优先、图数据库后置

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构/知识图谱负责人
- Related: SPK-002, NXW-GRAPH-001

## Context

R1 需要基础图谱、路径和证据查看，但不要求复杂图算法。Relation 是受 Schema、Evidence、审核和 Release 约束的业务对象，不能只存在于图数据库。

## Decision question

是否在 R1 强制引入 Neo4j/NebulaGraph，还是以关系表为业务事实并保留 GraphQueryPort？

## Options

1. 专用图数据库为权威；2. Relation 表为权威、图服务/投影可替换；3. 不提供图能力。

## Decision

选择 2。关系表保存版本、证据、权限和 Release 语义；GraphQueryPort 提供一跳/多跳、最短/因果路径候选能力。

## Consequences

正面：避免双写权威、简化 R1；专用图引擎可后加。负面：复杂遍历和大规模性能可能较弱，需要查询限制和基准。

## Migration risks

若 API 暴露具体图引擎查询语言，后续无法替换；图投影必须含 Release/tenant/space 维度并可重建。

## Validation

SPK-002 对固定 Release 验证关系查询、证据、权限、时间切片和重建；不满足再评估专用 Provider。
