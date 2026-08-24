# ADR-0013: 标识、租户隔离与通用元数据

- Status: Accepted
- Date: 2026-08-23
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Decision owners: 架构负责人、安全负责人
- Related: OQ-TENANT-001, NXW-ARCH-001

## Context

对象 ID、租户字段、时间、并发控制和审计字段若由各模块自行定义，将导致跨租户泄漏、事件无法对账和 API 不兼容。

## Decision

1. 对外稳定对象 ID 使用 UUIDv7 字符串；数据库列使用 PostgreSQL `uuid`。无法原生生成 UUIDv7 的边界可由应用层生成，不回退为业务可猜测序号。
2. 所有租户业务与治理记录从首次建表起包含 `tenant_id`；空间内记录同时包含 `space_id`。平台级配置必须显式标记为 platform scope，不以空租户值偷渡。
3. 时间一律保存 UTC `timestamptz`，API 使用 RFC 3339 UTC；展示层负责本地化。
4. 可变聚合包含单调递增 `version` 和 `updated_at`；HTTP 写操作使用强 `ETag`/`If-Match` 防止静默覆盖。
5. 通用审计元数据至少包含 `created_at/created_by/updated_at/updated_by`；不可变记录不伪造更新字段。
6. 数据库约束、仓储过滤和服务端授权共同阻断跨租户访问；前端传入的 tenant/space 不能作为唯一信任源。
7. 外部 ID 保存在命名空间化映射中，不替换内部稳定 ID。

## Consequences

索引和唯一约束必须以租户/空间维度设计；测试必须覆盖相同 ID 线索、不同租户访问和事件对账。UUIDv7 的生成实现必须被封装，避免业务层绑定某个库。

## Compatibility and migration

后续改变 ID 类型、租户键或时间语义属于破坏性变更，必须新增 ADR 和可回滚迁移；不得修改历史迁移。

## Validation

M0 契约测试验证 ID、UTC、资源元数据和租户字段；M1 起的每个仓储/接口补充跨租户阻断测试。
