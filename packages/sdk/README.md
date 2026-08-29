# NEXWEAVE SDK

M3 提供 Python 异步客户端与 TypeScript 客户端。两者均以版本化 `/api/v1`、Bearer token、W3C `traceparent`、`Idempotency-Key` 和强 ETag 为边界，不绕过公共 API 访问数据库、对象存储或 Temporal。

当前延续 M1 身份/空间和 M2 工作流能力，并新增 M3 Source 上传会话/完成、导入批次、列表/详情/版本、下载、reparse/retry、Segments、净化预览、失效与归档 typed API。Source 方法只驱动 `nexweave.source-ingestion.v2`；M2 v1 Stub 仍仅用于历史兼容。Schema、Compile、Evidence、Release 与 Query 仍不在 M3 SDK 范围。
