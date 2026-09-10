# ADR-0033：R1 + M9.5 阶段 A 运行稳定性

Status: Accepted for implementation under user's explicit Stage A instruction (2026-09-08).
前置：11B、ADR-0032；不改变 R1 Release/Evidence/SourceAnchor/Pack 语义，不进入阶段 B 或 M10。

1. ForecastRun 创建和 durable delivery 记录同事务。API 返回 202 表示已受理；Temporal 临时不可用不丢失任务。后台 adapter 对账重试投递；数据库不是第二套 Workflow 引擎，运行事实仍由 Temporal/Activity 驱动。
2. 新建预测使用 `nexweave.forecast.v2`。保留 v1 供历史执行重放；v2 使用活动 heartbeat、有限重试/超时。杀死 worker 后 Temporal 能恢复活动；不改写已完成制品。
3. 新增 delivery / worker lease 表（0011_m95a），记录投递错误/尝试/下一轮、原始 trace、重试来源、worker 存活。历史非终态任务纳入对账；历史终态保持不变。连接失败只记安全错误码，明确显示等待恢复。
4. 取消需当前空间 compile.create 权限及幂等键。先锁定数据库终态 CANCELLED，阻止任何晚到活动发布制品，再可靠请求 Temporal 取消；CPU 推理可能继续到当前调用结束，不保证即时算力抢占。
5. “重新运行”仅允许 FAILED/CANCELLED，创建新 Run，原任务/制品不可修改；关联 retry_of，复用原请求、已冻结 Context 和模型 revision。重新鉴权和验证 Source；不绕过撤销权限或失效源。
6. 对账只处理非终态或待发取消指令：未知 QUEUED 执行可投递；RUNNING 丢失 Temporal 历史则显式失败，不静默新建历史。Temporal 已失败/取消/超时映射为终态；完成却没有制品记一致性错误。
7. Worker 健康是独立可选能力；离线不拖垮 R1 API readiness。通过空间鉴权的运行状态接口展示 worker、队列与投递状态。统一本地启动支持现有 Compose + 可选隔离 CPU worker，使用进程锁避免重复启动，明确持久服务化仍限本地。
8. 版本以代码常量标识 M9.5/A，环境构建标签独立保留。W3C traceparent 在 HTTP 边界校验并建立请求专属 trace；不能继承其他请求残留的当前 span。业务审计、ProblemDetails 和响应使用同一请求 trace。
9. 只在新建合成隔离空间执行 R1 Source→Compile→Review→Release→Query/rollback 软件验收。测试角色动作不冒充真人专家批准或工业案例。补充投递中断、worker 崩溃恢复、取消晚到写、失败重跑、并发追踪和权限负向验证。

完成须提交运行证据、回归结果、迁移升降级结果、文档与风险清单。保持 Forecast 与已发布知识分离；阶段 B/C UI/知识引用深化不在本轮。
