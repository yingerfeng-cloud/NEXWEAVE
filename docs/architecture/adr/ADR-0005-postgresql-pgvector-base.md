# ADR-0005: PostgreSQL + pgvector 作为 R1 统一数据基座

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构/数据负责人
- Related: OQ-SEARCH-001, SPK-002

## Context

R1 需要事务业务事实、权限过滤、全文、向量和关系查询。首期同时引入 OpenSearch、Milvus 和图数据库会增加一致性、运维和重建成本。

## Decision question

R1 是否以 PostgreSQL 为业务权威，并以 pgvector/FTS/Relation 表提供 MVP 查询投影？

## Options

1. PostgreSQL + pgvector/FTS；2. PostgreSQL + 独立搜索/向量/图全套；3. 文档/图数据库为核心权威。

## Decision

选择 1 作为 R1 默认，保留 Search/Vector/Graph Port。专用引擎只有在 SPK-002 证明指标或能力不满足时引入。

## Consequences

正面：事务和权限过滤简单、依赖少、投影可重建。负面：混合检索、超大向量/图遍历的规模上限需实测；数据库资源隔离需设计。

## Migration risks

业务代码若使用 pgvector/FTS 方言会妨碍 Provider 替换和达梦适配。向量相似度不得进入事实置信度字段。

## Validation

SPK-002 使用代表性数据和固定 Release 验证 p95、吞吐、权限过滤、RRF、1—3 跳遍历和重建。
