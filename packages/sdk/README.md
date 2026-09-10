# NEXWEAVE SDK

M5 提供 Python 异步客户端与 TypeScript 客户端。两者均以版本化 `/api/v1`、Bearer token、W3C `traceparent`、`Idempotency-Key` 和强 ETag 为边界，不绕过公共 API 访问数据库、对象存储或 Temporal。

当前延续 M1 身份/空间、M2 工作流、M3 Source/Parse 与 M4 Schema/Domain Pack 能力，并新增 M5 CompileJob、知识实体读取、Wiki 草稿读取/受保护区编辑/版本读取 typed API。Source、Pack 与 Compile 分别驱动 v2 业务 Workflow；M2 v1 Stub 仅用于历史兼容。Review、Release 与 Query 仍不在 SDK 已实现范围。
