# 阶段 A：R1 + 时态知识稳定基础执行报告

日期：2026-09-09（Asia/Shanghai）。依据用户明确下发、11C 任务书、ADR-0033。结论：**阶段 A 本地技术验收通过，已恢复可运行状态；不是 M9 专家验收或 Chronos 工业效果验收。**

## 实际完成

- 统一 `make dev-up / dev-down / dev-status`，可选 CPU worker 采用进程锁与依赖重连；重复启动不创建第二个 worker。代码版本为 `0.9.5-a1`，环境构建标签另行保留。
- ForecastRun 与投递记录同事务落盘；接口返回 202 后，Temporal 故障可自动补发。v2 Workflow 增加活动心跳、有限重试/超时和终态对账；保留 v1 历史兼容。
- 取消立即阻止制品发布；失败/取消重跑创建新 Run，保留旧记录，关联 retry_of 并复用冻结 Context/请求/模型版本。当前权限与源有效性仍重新检查。
- 既有运行态页面增加服务离线提示、中文任务状态、取消与重跑；网络重试保留幂等键。切换空间清除旧空间运行记录。
- 修复跨请求 OpenTelemetry span 继承，响应、审计和错误保持请求自身 trace。

## 验证结果

| 检查 | 实测结果 |
|---|---|
| Python 回归 | 142 passed，5 个 integration 标记测试未在本次 pytest 中运行；真实服务演练另列 |
| 前端 | 26 passed；类型、lint、生产构建通过；本轮未追加人工视觉验收 |
| 代码/契约 | mypy 96 模块、Ruff、导出 JSON Schema/OpenAPI、SDK 类型/格式检查通过 |
| R1 完整软件链路 | 独立合成空间真实 Source→Compile→分权 Review→Evidence/Claim→Quality Gate→两次 Release→带引用 Query、拒答、幂等重放、导出、投影重建、指针回滚 |
| worker 崩溃 | 运行中核实 PID 后强杀；真实 Temporal 历史显示上次失败为 HEARTBEAT、恢复于 attempt=2；只提交 1 个 ForecastArtifact |
| 投递故障 | Temporal 停止时 API 返回 202；任务为 QUEUED/RETRYING、无制品；服务恢复后自动成功 |
| 取消与重跑 | 运行中及排队取消均无制品；新运行复用原冻结 Context/请求/模型版本；错误输入重跑仍显式失败 |
| 安全与不可变 | 取消/重跑/运行状态 3 项越权请求均 403；既有绑定/运行/制品越权拒绝、幂等冲突 409、3 张不可变表守卫通过；三个成功结果对象哈希与数据库一致 |
| HTTP 追踪 | 直连 API 单长连接上传 288,016 字节 CSV，随后 12 个串行请求和 24 个并发请求，trace mismatch=0；单元测试另覆盖继承 span 和错误 traceparent |
| 迁移 | 独立数据库升至 0011、降至 0010，再走历史降级/升级；旧哨兵数据保留；真实投递 SQL 的 NULL/非 NULL 参数执行通过 |
| 最终运行 | 统一入口完成；Compose 服务已恢复，预测 worker ready，重复启动保持同一 PID |

真实恢复演练发现了可空投递错误字段的 PostgreSQL 参数类型推断问题，已修复并纳入实际 SQL 回归。另纠正验证脚本对既有 Wiki 候选证据 API 和 Temporal 重试历史结构的理解，没有为配合测试新增候选接口或伪造超时事件。

机器可读 ID、manifest checksum、恢复结果见 [阶段A_运行证据.json](阶段A_运行证据.json)。R1 测试空间为 `01a081cc-9733-7d3f-9330-d068e17d273e`，所有材料与评审角色均为显式合成软件测试，不属于 M9 真实专家批准。调试途中形成的测试空间保留，没有删除用户数据。

## 迁移、安全与证据边界

唯一新迁移 `0011_m95a` 增加 `forecast_delivery`、`forecast_worker_leases`，并回填旧运行投递记录。10 份历史迁移、3 份依赖锁文件及核对的 Release/Evidence/SourceAnchor 实现文件与阶段 A 输入快照一致。旧 ForecastArtifact 不重写；Forecast 仍为模型派生结果，不能替代 Evidence、Observed Fact 或 Released Knowledge。

无新增第三方依赖、无新外部模型传输、未提交凭据、未 commit/push。运行记录只汇总合成测试 ID 和安全状态；原始日志、环境和本地模型仍留在忽略目录。

## 未关闭风险与停止边界

- Chronos-2 已有真实本地推理和恢复能力，工业精度/校准/误报、真实 P-101 授权数据及专家阈值仍未验证，不能称为现场完全可用。
- 本地管理器针对 macOS/Linux；整机重启或进程强杀后使用统一入口恢复，尚非生产常驻服务或多租户规模容量验收。对账为有界串行批次，后续扩容需验证公平性与故障时延。
- 取消阻止发布，不保证瞬时停止 CPU；可能留下无正式制品记录引用的存储对象，后续需要清理策略。Workflow 20 分钟超时后显式失败，可保留输入重新运行。
- 绑定向导、签名时序 Domain Pack、固定 Release 的 RCA/规程/案例引用合成和工业 Benchmark 保持后续事项；OQ-LK-007 Graph 旧版本/隔离疑点未由本轮关闭。
- M9 专家/阈值 P0、外部 CI 和生产供应链风险保持原状态。**本次停止在阶段 A，不进入阶段 B 或 M10。**

需求追踪：NXW-LK-A-001～005 已记录 VERIFIED，限制见矩阵。运行/恢复/验证命令见 [阶段 A 运行手册](../STAGE_A_RUNBOOK.md)。

## 本轮变更文件

以下清单基于阶段 A 开始前的本地输入快照及新增文件整理，不将工作区此前 M9/M9.5 大量未提交修改算作本轮工作。

- `.env.example`
- `AGENTS.md`
- `ARCHITECTURE_BASELINE.md`
- `docs/INDEX.md`
- `Makefile`
- `OPEN_QUESTIONS.md`
- `README.md`
- `apps/api/src/nexweave_api/app.py`
- `apps/api/src/nexweave_api/forecast_execution.py`
- `apps/api/src/nexweave_api/forecast_gateway.py`
- `apps/api/src/nexweave_api/forecast_recovery.py`
- `apps/api/src/nexweave_api/forecast_repository.py`
- `apps/api/src/nexweave_api/forecast_routes.py`
- `apps/api/src/nexweave_api/settings.py`
- `apps/api/src/nexweave_api/trace_boundary.py`
- `apps/api/src/nexweave_api/workflow_gateway.py`
- `apps/api/tests/test_app.py`
- `apps/api/tests/test_stage_a.py`
- `apps/web/src/LivingKnowledge.test.tsx`
- `apps/web/src/M7Knowledge.test.tsx`（仅格式校准）
- `apps/web/src/LivingKnowledge.tsx`
- `apps/web/src/api.ts`
- `apps/web/src/livingTypes.ts`
- `compose.yaml`
- `docs/architecture/adr/ADR-0033-stage-a-runtime-recovery.md`
- `docs/development/STAGE_A_RUNBOOK.md`
- `docs/development/reports/NEXWEAVE_阶段A_稳定基础执行报告.md`
- `docs/development/reports/阶段A_运行证据.json`
- `docs/development/tasks/11C_NEXWEAVE_阶段A_稳定基础.md`
- `docs/governance/DEPENDENCY_BASELINE.md`
- `docs/governance/REQUIREMENTS_TRACEABILITY_MATRIX.md`
- `migrations/versions/0011_m95a_delivery.py`
- `packages/contracts/openapi/nexweave-platform-v1.openapi.json`
- `packages/contracts/schemas/forecast-command.schema.json`
- `packages/contracts/schemas/forecast-run.schema.json`
- `packages/contracts/schemas/forecast-runtime.schema.json`
- `packages/contracts/src/nexweave_contracts/forecast.py`
- `packages/contracts/src/nexweave_contracts/runtime.py`
- `packages/contracts/src/nexweave_contracts/schema_export.py`
- `scripts/bootstrap_env.py`
- `scripts/check_migrations.py`
- `scripts/local_runtime.py`
- `scripts/run_m95_worker.py`
- `scripts/verify_m6.py`
- `scripts/verify_m7.py`
- `scripts/verify_m95.py`
- `scripts/verify_stage_a_r1.py`
- `scripts/verify_stage_a_records.py`
- `scripts/verify_stage_a_recovery.py`
- `scripts/verify_stage_a_trace.py`
- `workers/kernel/src/nexweave_worker_kernel/forecast_main.py`
- `workers/kernel/src/nexweave_worker_kernel/forecast_workflow_v2.py`
