# NEXWEAVE M2 执行结果

## 1. 总体结论

- 阶段：**通过**。M2 Temporal 可靠知识工作流内核、任务投影、任务中心、真实故障恢复纵向链路与官方时间跳跃门禁均已完成；远程全局 CI 和镜像供应链回执已取得。
- 是否满足进入下一阶段条件：**是（M2 技术门禁与正式验收均已完成）**。用户于 2026-08-25 正式验收 M2；M3 仍须用户单独明确下发，不得自行进入。
- Git 基线：M1/M2 交付提交前 HEAD 为 `727811f`；用户于 2026-08-25 授权使用仓库既有 Git 身份提交并 push。功能门禁提交 `ddbcc6e` 已在 `origin/main`，GitHub Actions run `32808198635` 全部通过。
- 阶段边界：M2 七类 Workflow 只执行可靠内核 Stub，明确返回 `business_features_implemented=false`；未实现 M3 Source/解析或 M4+ Schema、真实 Compile、Review 业务、Release、Query、GridCrew/RCA 功能。

## 2. 实际完成范围

### Workflow 实现

- 建立专用 Temporal Namespace `nexweave-dev`（开发保留 7 天）、独立 Workflow/Activity Task Queue 和非 root `worker-kernel` 部署；M0 health Worker 继续独立运行；
- 实现七个显式版本化 Workflow：SourceIngestion、KnowledgeCompile、HumanReview、QualityEvaluation、KnowledgeRelease、DomainPackInstall、GridCrewFeedbackIngestion；每类使用稳定业务键派生 Workflow ID，并保存 Temporal Run ID；
- 每类包含可扩展三步计划；M2 Activity 只验证引用/策略边界并写 Stub 投影，不创建任何后续业务对象；
- 实现 pause/resume/cancel、claim/request/provide input、approve/reject、retry 命令，durable approval wait、300 秒升级事件、状态查询与重复 Update 结果缓存。

### 可靠性

- Workflow 定义保持确定性，无网络、数据库、文件、模型或系统时钟 I/O；所有投影/步骤/补偿写入位于独立 Activity；
- Activity 具备 start/schedule timeout、heartbeat、指数重试、最大 attempts 和不可重试错误分类；故障注入验证首 attempt 失败、第二 attempt 成功；
- 取消按已完成步骤逆序补偿；FAILED/TIMED_OUT 提供同 Workflow ID 新 Run 的 retry 路径；
- 真实演练覆盖七类任务逐类取消、重复创建/命令、关闭 Run 对账失败后以同 Workflow ID 新 Run 重试恢复、Worker 停止/恢复、历史 Replay、投影破坏/对账修复、Event 防篡改与 Audit/Outbox；
- 官方 SDK time-skipping 测试已在本地及 GitHub Actions 独立 Linux x64 job 通过；测试跳过 300 秒 durable timer，并验证升级事实和后续人工批准完成。

### 任务中心

- 新增真实 API 驱动的任务列表、类型/状态、详情、步骤、追加日志、错误、进度、服务端允许动作、投影同步状态与对账；
- 支持七类内核任务创建、暂停/继续/取消/人工决定/重试、空/加载/错误/重试状态；
- 支持 `/compile` 与 `/compile/{task_id}` 深链接、刷新恢复和浏览器返回；页面明确 Temporal 为执行权威、PostgreSQL 为查询投影和 M2 Stub 边界；
- 服务端执行 tenant/space RBAC+ABAC、状态、ETag 和幂等校验，前端不授予权限或推进任务。

### 数据、API、事件与 SDK

- 新增 WorkflowTask、WorkflowStep、WorkflowTaskEvent 领域/契约；任务包含 tenant、space、status、version、creator/updater、stable Workflow ID、Run ID 与 projection revision；
- 新增 create/list/detail/command/reconcile API，写接口使用 `Idempotency-Key`，命令使用强 `If-Match`，稳定错误覆盖 business key 冲突、状态拒绝、版本失败与 Temporal 不可用；
- 新增 `io.nexweave.workflow.task-changed.v1` 最小 Outbox payload 与 JSON Schema；逐步骤数据库 Event 追加式，不将敏感输入放入公共事件；
- 扩展 typed Python/TypeScript SDK 和 SDK 契约测试；OpenAPI 3.1、JSON Schema snapshot 与实现一致；
- 新增 `0003_m2_temporal_kernel` 追加迁移，未修改历史迁移。

### 文档与治理

- ADR-0020 Accepted，冻结执行/投影权威、标识、控制、重试、补偿与业务 Stub 边界；
- 更新架构/API/Event/Workflow/数据/状态/C4 baseline、需求追踪、依赖、迁移、质量门禁、CHANGELOG、项目状态与文档索引；
- 新增 M2 实施计划、运行手册、本执行报告和可靠性/故障演练报告；`OQ-REVIEW-001` 未被 300 秒内核 timer 静默关闭。

## 3. 新增或修改文件

### 根工程、基础设施与 CI（NXW-ARCH-002、NXW-NFR-AVL-002）

- `.env.example`, `compose.yaml`, `Makefile`, `package.json`, `pyproject.toml`, `scripts/bootstrap_env.py`：M2 Namespace/队列/版本、kernel Worker 与统一验证；
- `workers/kernel/Dockerfile`, `workers/kernel/src/nexweave_worker_kernel/*`：非 root Worker、七类 Workflow、Activity 与运行入口；
- `.github/workflows/ci.yml`：M2 质量/Compose 验证与 kernel Worker 镜像矩阵；
- `scripts/verify_m2.py`：七类真实 E2E、可靠性、安全/证据、故障恢复和 Replay。

### 领域、应用、契约、API 与迁移（NXW-COMPILE-001、NXW-ARCH-001/002）

- `packages/domain/src/nexweave_domain/workflow.py`, `access.py`, `__init__.py`：类型、状态、命令、稳定 ID、步骤计划和权限动作；
- `packages/application/src/nexweave_application/ports.py`, `__init__.py`：厂商中立 `WorkflowGatewayPort`；
- `packages/contracts/src/nexweave_contracts/workflow.py`, `schema_export.py`, `__init__.py` 与生成 Schema/OpenAPI：canonical M2 contracts；
- `apps/api/src/nexweave_api/workflow_gateway.py`, `workflow_repository.py`, `workflow_routes.py`, `app.py`, `settings.py`：Temporal adapter、查询投影、控制与对账 API；
- `migrations/versions/0003_m2_temporal_kernel.py`：Task/Step/append-only Event 投影与索引/trigger。

### Web、SDK 与测试（NXW-COMPILE-001、NXW-NFR-PERF-002）

- `apps/web/src/TaskCenter.tsx`, `App.tsx`, `api.ts`, `types.ts`, `styles.css`, `App.test.tsx`：真实任务中心与恢复/错误/UI 测试；
- `packages/sdk/python/nexweave_sdk/*`, `packages/sdk/typescript/src/client.ts`, `packages/sdk/README.md`：M2 typed SDK；
- `packages/domain/tests/test_m2_workflow.py`, `packages/contracts/tests/test_m2_workflow_contracts.py`, `tests/contract/test_m2_sdk.py`, `workers/kernel/tests/*`, OpenAPI/architecture/app tests：领域、契约、SDK、确定性、Replay/time-skip 骨架与 UI 回归。

### 架构、治理与使用文档

- `docs/architecture/adr/ADR-0020-m2-temporal-kernel-and-task-projection.md` 与 ADR index；
- `ARCHITECTURE_BASELINE.md`、API/Event/Workflow/Data/Domain/State/C4 baseline；
- `docs/governance/REQUIREMENTS_TRACEABILITY_MATRIX.md`, `DEPENDENCY_BASELINE.md`, `MIGRATION_FIXTURE_STRATEGY.md`, `QUALITY_GATES.md`；
- `docs/development/M2_IMPLEMENTATION_PLAN.md`, `M2_RUNBOOK.md`, 两份 M2 报告，以及 `README.md`, `docs/INDEX.md`, `PROJECT_STATUS.md`, `OPEN_QUESTIONS.md`, `CHANGELOG.md`, `AGENTS.md`。

以上 M2 文件与已验收的 M1 交付作为同一受控变更集提交；没有覆盖、重置或删除用户修改。

## 4. 领域对象、API、事件和 Workflow 变更

- 新增：WorkflowType（7 类）、WorkflowTaskStatus/StepStatus、WorkflowCommand、稳定 Workflow ID/Temporal name/步骤计划；WorkflowTask/Step/Event、command/reconcile contracts；
- API：`POST/GET /spaces/{space_id}/workflow-tasks`、`GET /workflow-tasks/{task_id}`、`POST /workflow-tasks/{task_id}/commands`、`POST /workflow-tasks/{task_id}/reconcile`；
- 事件：`io.nexweave.workflow.task-changed.v1` transactional Outbox；DB 内 WorkflowTaskEvent 使用稳定 event key 幂等并由 trigger 防更新；
- Workflow：新增七类 `nexweave.*.v1` 定义，Update/Signal、query、timeout/retry/heartbeat/cancel/compensation；Activity 位于独立 queue；
- 修改：M1 角色动作增量加入 `workflow.create/read/control/review/reconcile`；API/Web/SDK 版本提升到 M2；M1 平台接口保持兼容；
- 兼容性影响：全部为 `/api/v1` additive 路径、可选契约和 `0003` 新迁移；没有修改 SourceAnchor、Evidence 或 Release 语义；
- ADR：ADR-0020 Accepted；未改写历史 ADR 或 `0001`/`0002` 迁移。

## 5. 测试与验证

### 已通过

- `make check PYTHON=.venv/bin/python`：Ruff format/lint、mypy（48 source files）、ESLint、TypeScript、Prettier、SDK check、Web production build 全部通过；Python **39 passed / 2 integration deselected**，Web **6 passed**，契约子集 **17 passed**；
- `.venv/bin/python scripts/verify_m2.py`：七类真实 Workflow/逐类取消、Update 幂等、Activity retry、终止 Run 对账后 retry 新 Run、approval、pause/resume、cancel/compensation、projection reconcile、Worker restart 和 history replay 全部通过；
- 验证脚本同时确认 workflow Audit/Outbox 均非零、Event UPDATE 被数据库 trigger 拒绝；
- 隔离真实 PostgreSQL 数据库 `base → head → base → head` 通过；当前开发数据库最终为 `0003_m2 (head)`；
- `secret_scan.py`、`pip check`、`docker compose config --quiet`、`git diff --check` 通过；
- Python 与 JavaScript production dependency audit 均为 `No known vulnerabilities found`；
- 最终八个 Compose 服务运行，带 healthcheck 的服务均 healthy；kernel Worker 运行中。故障注入 WARNING 为预期首 attempt 失败，任务均按断言恢复。

### 远程闭环与未执行项

- `workers/kernel/tests/test_time_skipping.py` 首次初始化外部 test-server binary 296 秒未完成并人工中止；修正测试 Activity 类型并设置显式缓存目录后，本地真实执行 `1 passed`，run `32808198635` 的独立 `temporal-time-skipping` job 通过；
- run `32808198635` 的 quality、time-skipping、Compose integration、四个 application-image 与 RustFS approval 共八个 job 全部通过；API、Web、worker-health、worker-kernel 与 RustFS 的双架构 CycloneDX SBOM、可修复 HIGH/CRITICAL CVE 阻断、Cosign 签名和验证均成功并上传制品；
- 未执行生产 Temporal 多集群/HA/DR/升级、生产 OIDC/Secret/HTTPS、容量/性能或国产浏览器专项认证。

## 6. 数据库与迁移

- 迁移文件：`migrations/versions/0003_m2_temporal_kernel.py`，down revision 为已验收的 `0002_m1`；
- 增量：`workflow_tasks`、`workflow_steps`、`workflow_task_events`，tenant/space/run/business/idempotency 索引/约束，以及 Event append-only trigger；
- 回滚验证：安全检查拒绝在当前数据库执行破坏性 downgrade；改用精确命名的一次性数据库完成 `base → 0001 → 0002 → 0003 → base → 0003`，随后仅永久删除该一次性数据库；当前数据库未降级；
- 数据兼容性：不修改历史迁移；Task/Step 是可修复查询投影，Event/Audit/Outbox 追加式；数据库不成为第二套 Workflow 状态机；
- 生产影响：降级会删除 M2 查询投影但不删除 Temporal history，必须先停写、备份并制定前向恢复/历史兼容计划，禁止直接在共享/生产执行通用 rollback check。

## 7. 安全、权限、审计与证据检查

- 任务 create/read/control/review/reconcile 均经过 M1 tenant/space RBAC+ABAC，服务端基于数据库角色与任务状态给出 allowed actions；客户端状态不授予权限；
- 写入使用 Idempotency-Key；命令使用强 ETag；重复 key 返回原结果，不同 hash/business payload 明确冲突；
- 任务、命令、Activity 投影与 reconcile 写入 Audit/Outbox；Event trigger 阻止原地篡改；trace/correlation 延续 M1 边界；
- `input_refs` 有数量/长度限制，只保存引用；工作流事件/日志不携带 Bearer token、Secret、对象正文或真实资料；
- Workflow 模块静态边界与 Replay 均通过，外部 I/O 仅 Activity/API adapter；没有普通后台线程、Celery 或 DB polling 替代 Temporal；
- M2 没有调用模型、Parser、Connector 或对象内容，也没有创建 SourceAnchor/Evidence/Release；Stub 结果明确不是业务证据；
- Secret scan/SCA 通过，无新增依赖，无客户/设备/RCA 分支或真实敏感 fixture。

## 8. 风险与遗留项

### P0

- 无已知 P0；M1 前置平台能力可用，M2 最低真实执行、控制、恢复、投影、迁移、权限和审计链路成立。

### P1

- 本地单节点 Temporal 不关闭生产 Namespace 保留、版本升级兼容、HA/DR、容量与 RPO/RTO 门禁。

### P2

- M2 的 300 秒批准 timer 仅验证 durable escalation，不冻结 M6 风险等级、职责分离、批量审核或业务 SLA；`OQ-REVIEW-001` 保持 OPEN；
- Continue-As-New、超大 history 与跨 Namespace 策略待真实长任务规模/部署拓扑明确后验证；
- OTel contrib `0.65b0` 与 RustFS RC 风险延续既有跟踪，不因 M2 Stub 工作流关闭。

## 9. 需求追踪更新

- 已完成需求 ID：`NXW-ARCH-002`（七类 Workflow 确定性、I/O Activity 隔离与真实 Replay）；
- 部分完成需求 ID：`NXW-COMPILE-001`（通用任务/步骤/控制/故障恢复，真实 Compile 待 M5）、`NXW-NFR-PERF-002`（异步进度投影存在，≤3 秒未作批准负载认证）、`NXW-NFR-AVL-002`（Worker 重启/Replay 通过，真实 Compile 断点与 Release 回滚待 M5/M7）；
- 持续完成：`NXW-ARCH-001`（domain/contracts/application Port 依赖边界）；
- 未覆盖需求 ID：M3 Source/解析、M4 Schema/Pack、M5 真实 Compile/Wiki、M6 Claim/Evidence/Conflict/Review、M7 Quality/Release/Query/Graph、M8 Integration/GridCrew、M9 RCA 试点，以及正式性能/HA/DR/质量阈值；均保持 BASELINED 或 PARTIAL，不以 Stub 提前关闭。

## 10. 停止声明

M2 已于 2026-08-25 正式验收并停止；M3 尚未下发，未自行进入 M3 或任何后续 Milestone。
