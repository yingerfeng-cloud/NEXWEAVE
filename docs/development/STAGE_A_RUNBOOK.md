# R1 + M9.5 阶段 A 本地运行手册

适用任务书 11C / ADR-0033，代码版本 `0.9.5-a1`。本手册不代表 M9 专家验收、工业预测效果验收或 M10 下发。

## 启动与状态

```bash
make dev-up
make dev-status
make dev-down
```

`dev-up` 保留现有 Compose 数据卷，自动升级数据库，并在 `.nexweave-data/forecast-venv` 和锁定模型已安装时启动独立 CPU worker。进程锁防止重复启动；缺少可选环境/模型时明确报告预测不可用，R1 仍可启动。安装说明沿用 M9.5 首片报告及 `requirements/forecast.lock`，不自动下载模型或新增依赖。

单独控制预测服务：

```bash
python3 scripts/local_runtime.py worker-start
python3 scripts/local_runtime.py status
python3 scripts/local_runtime.py worker-stop
```

状态文件与日志位于忽略目录 `.nexweave-data`；不得提交环境密钥或原始敏感日志。控制脚本在停止前核实 PID 对应完整命令，不发送强制终止。正常依赖断线自动重连；整机重启或进程被强制终止后重新执行 `make dev-up`。当前不是操作系统服务/生产部署承诺。

Wiki、Graph、Ask、Schema、集成中心原有运行态页显示预测服务在线/离线及队列。离线并不等于任务丢失。API `/version` 的 `implementation_version` 表示代码版本；`build_version` 保留部署环境提供的构建标签，旧 `.env` 不会被静默覆盖。

## 任务语义

- 创建返回 202 表示任务和投递记录已在同一数据库事务落盘。投递故障自动退避重试，稳定 Workflow ID 防止重复启动。
- 新运行使用 v2 Workflow；v1 保留供历史运行重放。v2 活动每 3 秒心跳、15 秒心跳超时、最多 3 次活动尝试；每次活动最长 10 分钟，整个运行最长 20 分钟。
- 取消立即将任务置为不可变 CANCELLED 并阻止晚到结果发布，随后可靠请求 Temporal 取消。CPU 计算可能继续到本次调用结束，不承诺即时释放算力。
- 失败/取消后“以原输入重新运行”创建新 Run，并记录 `retry_of`。复用原请求、已有冻结 Context、模型版本；源失效、权限撤销、模型版本不符仍会拒绝。输入本身错误时，按原输入重跑也会失败。
- 重跑与创建遇到网络响应丢失时，前端保留同次操作幂等键；更改场景输入才生成新操作。已成功运行和制品不能取消、改写或原地重跑。
- worker 健康采用 20 秒租约，不读取机器路径/凭据；空间运行数量受当前权限和密级过滤。预测 worker 离线不影响 R1 API readiness，其他基础依赖故障仍影响 readiness。

## 可复现验证

```bash
.venv/bin/python scripts/verify_stage_a_r1.py
.venv/bin/python scripts/verify_stage_a_trace.py
.venv/bin/python scripts/verify_stage_a_recovery.py crash
.venv/bin/python scripts/verify_stage_a_recovery.py cancel
.venv/bin/python scripts/verify_stage_a_recovery.py delivery
.venv/bin/python scripts/verify_stage_a_recovery.py guards
.venv/bin/python scripts/verify_stage_a_records.py
.venv/bin/python scripts/verify_m95_guards.py
make migration-check
```

R1 验证新建隔离空间，使用合成文本与脚本测试角色，通过现有 API 完成 Source→Compile→Review→Evidence/Claim→Quality Gate→Release→Query、拒答、导出、投影重建和指针回滚。不要将脚本角色动作解释为真人专家评审。

恢复演练使用既有明确标记 SYNTHETIC 的 P-101 绑定。`crash` 会核实并强制终止自身预测进程；`delivery` 会短暂停止本地 Temporal；均在结束时恢复服务。不要在承载现场任务的环境直接执行这些故障演练。结果写入 `.nexweave-data/stage-a-*.json`；对外验收记录见阶段 A 执行报告。

## 数据迁移与回退

唯一新增迁移 `0011_m95a` 增加投递记录和 worker 租约两表，回填既有预测任务的投递状态；不修改历史迁移、Evidence/Release 表或旧制品。原始调用 trace 在旧运行无记录时使用运行 UUID 的稳定回填值，并不冒充旧 HTTP trace。

回退只适用于停止新 API/worker 后，与旧版本代码一起降级到 `0010_m95`；会移除投递重试和租约元数据，预测运行与制品保留。活动 v2 的历史需要继续保留 v2 worker 兼容处理；不能在有 v2 非终态任务时直接降级旧 worker。隔离数据库已验证升级、降级、再升级及旧数据保留。
