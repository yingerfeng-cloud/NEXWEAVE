# NEXWEAVE SDK

M2 提供 Python 异步客户端与 TypeScript 客户端。两者均以版本化 `/api/v1`、Bearer token、W3C `traceparent`、`Idempotency-Key` 和强 ETag 为边界，不绕过公共 API 访问数据库、对象存储或 Temporal。

当前覆盖 M1 的身份、知识空间、成员、审计和托管对象链路，并新增 M2 工作流任务列表、详情、创建、控制与对账。七类 M2 Workflow 只暴露可靠性内核任务，Source、Schema、Compile、Release 与 Query 业务对象必须等待对应 Milestone 下发。
