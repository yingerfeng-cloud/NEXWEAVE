# NEXWEAVE M2 可靠性与故障演练报告

> 日期：2026-08-24
> 环境：本地 Docker Compose、Temporal Server 1.29.6、Temporal Python SDK 1.31.0、PostgreSQL 17
> 数据：仅合成开发身份、空间、业务键与 Stub 引用；无客户或 RCA 资料

## 1. 结论

M2 的七类可靠 Workflow 内核、Activity 重试、命令幂等、人工等待、暂停/恢复、取消补偿、投影对账、Worker 恢复和历史 Replay 已在真实 Temporal/PostgreSQL 环境通过。官方 SDK 时间跳跃测试代码已实现，但外部 test-server binary 初始化未完成，未取得通过结果；因此可靠性验收为**有条件通过**。

M2 不生成 SourceVersion、知识草稿、ReviewAction、Release、Pack Installation 或 GridCrew intake。所有成功结果均明确包含 `business_features_implemented=false`，不能作为 M3+ 功能证据。

## 2. 环境与拓扑证据

- Namespace：`nexweave-dev`，开发保留期 168 小时；
- Workflow Queue：`nexweave-m2-workflows`；Activity Queue：`nexweave-m2-activities`；
- Worker：独立 `worker-kernel`，Workflow/Activity 分离 poll，容器以非 root 用户运行；
- 最终 Compose：PostgreSQL、Redis、RustFS、Temporal、API、Web 为 healthy；health Worker 与 kernel Worker 运行中；
- 最终数据库 revision：`0003_m2 (head)`。

## 3. 演练矩阵

| 场景 | 注入/操作 | 期望 | 真实结果 |
|---|---|---|---|
| 七类 Workflow | 逐类通过真实 API 创建 | 普通类型成功；三类批准型等待决定后成功 | 通过；七类均进入独立 Temporal history 并完成 Stub 步骤 |
| Activity 网络/瞬态失败等价注入 | `retryable-*` 步骤首个 attempt 抛 `M2_INJECTED_TRANSIENT_FAILURE` | Temporal 按策略重试，不重复步骤业务事实 | 通过；Source 步骤 attempt 为 `[1,2,1]`，最终成功 |
| 重复创建 | 同幂等键重复、同 business key 新 key、冲突负载 | 返回同一任务；冲突负载返回稳定 409 | 通过 |
| 重复 Update | 对暂停任务以相同命令 key 重发 RESUME，并使用原 ETag | 返回原命令业务结果，不二次执行 | 通过；两次响应一致 |
| 人工等待/批准 | HumanReview、KnowledgeRelease、DomainPackInstall 到 WAITING 后 APPROVE | durable wait 后继续 | 通过；均到 SUCCEEDED |
| 暂停/继续 | 以 `start_paused=true` 创建，再 RESUME | PAUSED 可查询，继续后完成 | 通过 |
| 全类型取消 | 七类任务均从 PAUSED 发 CANCEL | 每一类最终 CANCELLED | 通过；七类均可取消 |
| 取消与补偿 | Source 首步骤完成后发 CANCEL | 已完成步骤逆序补偿，最终 CANCELLED | 通过；至少一个步骤为 COMPENSATED |
| 失败后重试 | 终止一个暂停 Run，对账为 FAILED，再发 RETRY/RESUME | 同一 Workflow ID 新 Run，业务 Task ID 不变并恢复成功 | 通过；新 Run 最终 SUCCEEDED |
| 投影损坏与修复 | 仅在合成目标上把 DB 投影改为 PAUSED/不同步 | Temporal 状态不变；reconcile 修复投影并追加事实 | 通过；恢复 SUCCEEDED，`repaired=true` |
| Worker 宕机 | 停止 `worker-kernel`，创建任务，再恢复 Worker | 任务停留 STARTING，恢复后继续 | 通过；最终 SUCCEEDED |
| History Replay | 从真实 Temporal 获取已完成 history，使用七类当前定义 Replayer | 无 nondeterminism | 通过 |
| Event 防篡改 | 尝试 UPDATE 一条 `workflow_task_events` | 数据库 trigger 拒绝 | 通过 |
| 审计与事件 | 统计 `workflow.*` Audit 与 Outbox | 均存在且非零 | 通过 |
| 时间跳跃 | 启动官方 `WorkflowEnvironment.start_time_skipping()` | 跳过 durable timer 并验证升级 | **未取得结果**；external binary 初始化 296 秒无完成后中止 |

## 4. 超时、重试与补偿策略

- Activity：start-to-close 15 秒、schedule-to-close 45 秒、heartbeat 5 秒；
- 重试：初始 1 秒、系数 2、最大间隔 5 秒、最多 3 次；`M2_KERNEL_POLICY_VIOLATION` 不可重试；
- 人工批准：M2 内核 300 秒 durable timer 到期后追加 `APPROVAL_TIMEOUT_ESCALATED`，不自动批准/拒绝，仍要求授权人工决定；
- 取消：设置取消意图，已完成步骤以 Activity 逆序补偿，保留步骤/命令/审计历史；
- 重试入口：仅 FAILED/TIMED_OUT，沿用稳定 Workflow ID 并创建新 Run；
- 投影：Activity 通过稳定 event key 幂等；数据库 projection revision 单调增加，Event 禁止 update/delete。

上述 300 秒仅为 M2 内核故障演练参数，不冻结 M6 的风险等级、升级责任人或业务 SLA；`OQ-REVIEW-001` 保持 OPEN。

## 5. 执行命令与结果

```text
make check PYTHON=.venv/bin/python
  Python: 39 passed, 2 integration deselected
  Contract subset: 17 passed
  Web: 6 passed
  Ruff/mypy/ESLint/TypeScript/Prettier/SDK/production build: passed

.venv/bin/python scripts/verify_m2.py
  M2 real verification passed: seven workflows, all-type cancellation,
  Update idempotency, Activity and failed-run retries, approval, pause/resume,
  compensation, reconciliation, worker restart and replay
```

独立迁移演练在一次性数据库完成 `base → head → base → head`；该数据库随后被永久删除，当前开发数据库未降级且最终仍是 `0003_m2 (head)`。

## 6. 可观测性与日志判断

- API/Web 访问日志只包含路径、状态、客户端类型与合成 ID，不包含 Authorization header；
- 故障注入阶段 Worker 会按 Temporal SDK 默认行为记录首个 attempt 的 WARNING/Traceback，错误类型固定为 `M2_INJECTED_TRANSIENT_FAILURE`；这是预期注入证据，后续 attempt 成功；
- 最终服务状态正常，未观察到未恢复的 Workflow 失败、API 未处理异常、Secret 或对象正文泄漏。

## 7. 风险与后续条件

### P0

- 无已知 P0。

### P1

- 官方 time-skipping test-server binary 未能初始化；需在可缓存/可联网的 CI runner 取得真实测试通过结果，才能关闭 M2 时间跳跃条件项；
- 当前变更已由用户授权本地提交但未 push，尚无对应远程全局 CI、双架构镜像 SBOM/CVE/Cosign 回执。

### P2

- 本地单节点演练不构成生产 Namespace 保留、Temporal 升级兼容、多集群 HA/DR、容量或 RPO/RTO 认证；
- Continue-As-New 与超大 history 在出现真实长流程/规模数据后验证；
- M6 人工审核升级策略仍由 `OQ-REVIEW-001` 决定。
