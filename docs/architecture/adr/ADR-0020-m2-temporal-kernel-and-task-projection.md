# ADR-0020: M2 Temporal 内核、任务投影与控制契约

- Status: Accepted
- Date: 2026-08-24
- Approval basis: 用户正式验收 M1 并下发 M2；ADR-0004、ADR-0016
- Related: NXW-ARCH-002, NXW-COMPILE-001, NXW-NFR-AVL-002

## Context

M2 首次把七类长任务从冻结词汇变成真实 Temporal 执行。后续业务聚合尚未实现，若 M2 Stub Activity 写入 Source、知识、Review、Release 或 GridCrew 对象，会越过 Milestone；若数据库或页面独立推进任务状态，则会形成与 Temporal 竞争的第二状态机。

## Decision

1. 本地/测试使用专用 Temporal Namespace `nexweave-dev`；生产 Namespace 由部署环境显式提供。Workflow queue 为 `nexweave-m2-workflows`，I/O Activity queue 为 `nexweave-m2-activities`，健康 Workflow 保留独立 queue。
2. 实现七个具名 Workflow：SourceIngestion、KnowledgeCompile、HumanReview、QualityEvaluation、KnowledgeRelease、DomainPackInstall、GridCrewFeedbackIngestion。它们共享版本化 M2 kernel 协议，但保留独立 Workflow type/name、稳定 ID prefix 和步骤计划。
3. M2 Workflow 只编排确定性状态、durable timer、Update/Signal、取消与补偿；不得导入数据库、HTTP、文件、对象存储、模型或厂商 Adapter。所有投影/审计 I/O 位于可重试、可心跳、幂等 Activity。
4. M2 Activity 只写 `WorkflowTask/Step/Event` 投影和内核演练结果，不创建后续 Milestone 业务对象。`STUB_SUCCEEDED` 表示执行内核步骤成功，不表示解析、编译、审核、发布、安装或反馈业务完成。
5. 业务任务 ID 使用 UUIDv7；Workflow ID 为冻结 prefix + tenant + business key，数据库唯一映射。重复创建使用现有公共幂等语义；同 key/同 request 返回同一 task/workflow，同 key/不同 request 冲突。
6. 公共控制使用 Temporal Update，以 client command/idempotency key 在 Workflow history 内去重；Signal 作为内部/异步兼容入口，执行相同状态校验。暂停、继续、领取、补资料、批准、驳回、取消只由 Workflow 决定。
7. 数据库投影保存最后 event key、projection revision 和 reconciliation 事实，只读展示，不由 cron/轮询推进。显式 `reconcile` 查询 Temporal describe/query 后修复投影，并写审计/Outbox；投影差异在 UI 明示。
8. retry 对已关闭且失败/超时的任务创建相同 Workflow ID 的新 Run，保留业务 task ID 与历史事件；不得创建重复业务任务。
9. Activity 分类固定 start-to-close/schedule-to-close/heartbeat timeout、指数 retry 和 non-retryable error allowlist。补偿只撤销 M2 可见投影/指针，不删除 Raw、审核历史或未来 Release。
10. 历史增长在 M2 以有限步骤/命令数量上限控制；Continue-As-New 在实际历史阈值证据出现后通过兼容 ADR 引入，不提前改变跨 Run 命令语义。

## Consequences

- M2 可真实验证七类 Workflow 的启动、等待、控制、重试、取消、补偿、Worker 恢复和投影修复，同时不伪造 M3—M8 业务结果。
- UI/API 读取 PostgreSQL 投影，详情同时展示 Temporal Run/投影同步信息；执行权威仍为 Temporal。
- API → Temporal → Activity → PostgreSQL 是跨系统链路；稳定 ID、Update 去重、Activity event key 和显式 reconciliation 共同处理崩溃窗口。

## Compatibility and migration

新增 `/api/v1/workflow-tasks` additive API、M2 event payload 和 `0003_m2_temporal_kernel` 迁移，不修改历史迁移。Workflow 名称/输入 schema 以 `.v1` 固定；破坏性 Workflow history 变化必须使用 Temporal versioning/新 type 并提供 replay 证据。

## Validation

- 七类 Workflow smoke、Replay、时间跳跃、Update/Signal 幂等与非法状态单元/集成测试；
- 真实 PostgreSQL migration upgrade/down/up、append-only event、投影 reconciliation；
- 真实 Temporal Worker 停止/重启、retryable Activity 失败、heartbeat、暂停/继续/取消/补偿；
- Web/API/DB/Temporal E2E 与权限、审计、trace、重复请求验证。
