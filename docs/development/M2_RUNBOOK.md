# NEXWEAVE M2 运行手册

> 适用范围：本地/验收环境中的 M1 平台基础与 M2 Temporal 可靠工作流内核。七类 Workflow 的 Activity 是明确的 Kernel Stub；本手册不授权 M3+ 业务实现或生产上线。

## 1. 运行拓扑

| 组件 | M2 责任 |
|---|---|
| API/Web | 身份、空间授权、任务创建/查询/控制/对账与任务中心 |
| Temporal `nexweave-dev` | Workflow 历史与执行状态权威，开发保留期 7 天 |
| `worker-kernel` | 从 `nexweave-m2-workflows` 取 Workflow、从 `nexweave-m2-activities` 取 Activity |
| PostgreSQL | WorkflowTask/Step/Event 查询投影、Audit、Outbox、幂等记录；不推进 Workflow |
| RustFS/Redis | 继续承载 M1 对象和就绪检查；M2 Stub 不读写业务对象正文 |

七类版本化 Workflow：SourceIngestion、KnowledgeCompile、HumanReview、QualityEvaluation、KnowledgeRelease、DomainPackInstall、GridCrewFeedbackIngestion。

## 2. 启动与健康检查

```bash
make env
make dev-up
docker compose ps
```

浏览器访问 `http://127.0.0.1:8080`，使用本地开发身份登录后进入“任务中心”。API 就绪端点为 `http://127.0.0.1:8080/api/v1/health/ready`。

查看受控日志：

```bash
make dev-logs
```

日志不得包含 Bearer token、Secret、对象正文或凭据。生产环境必须关闭 local development identity，配置 HTTPS OIDC 与外部 Secret Provider。

## 3. 任务操作语义

- 创建：必须位于调用者有权限的活动空间，提供稳定 `business_key` 与 `Idempotency-Key`；同一业务键返回同一任务，负载不一致返回明确冲突；
- 查询：列表与详情读取 PostgreSQL 投影，并明确标记投影来源；详情包含步骤、追加日志、ETag 与当前授权动作；
- 控制：暂停、继续、取消、人工决定与重试必须同时携带 `Idempotency-Key` 和详情返回的强 `ETag`；
- 取消：已完成步骤按逆序补偿，事实日志保留；
- 批准：HumanReview、KnowledgeRelease、DomainPackInstall 在人工决定前保持 durable wait；内核 300 秒超时仅记录升级事件，不自动批准或拒绝；
- 重试：仅 FAILED/TIMED_OUT 可重试；保持稳定 Workflow ID 并创建新 Run；
- 刷新/返回：可直接打开 `/compile/{task_id}`，页面从 API 恢复，不依赖浏览器内存状态。

## 4. 投影滞后与对账

Temporal 是执行权威。若详情显示投影不同步，具备 `workflow.reconcile` 权限的管理员可在任务详情执行“对账修复”，或调用：

```text
POST /api/v1/workflow-tasks/{task_id}/reconcile
```

修复只覆盖可变 Task/Step 查询投影并新增 reconciliation Event、Audit 与 Outbox，不修改 Temporal 历史，也不更新/删除既有 `workflow_task_events`。

## 5. Worker 故障恢复

开发演练可停止并恢复 M2 Worker：

```bash
docker compose stop worker-kernel
docker compose start worker-kernel
```

Worker 停止时新任务可停留在 STARTING；恢复后 Temporal 重新派发并继续。不要通过数据库手工把任务改成成功。若恢复后仍无进展，检查 Namespace、两个 Task Queue、Worker 日志、API 与 PostgreSQL/Temporal 就绪状态，再执行投影对账。

## 6. 验证

```bash
make check PYTHON=.venv/bin/python
make verify-m2 PYTHON=.venv/bin/python
```

`verify-m2` 会创建合成任务，并包含 Worker 停止/恢复和故意损坏一条任务投影后修复的演练；只能在本地/一次性验收环境运行。它还验证工作流审计/Outbox 与 Event 追加保护。

官方时间跳跃用例位于 `workers/kernel/tests/test_time_skipping.py`，需要 Temporal SDK 官方 test-server binary 可用：

```bash
.venv/bin/python -m pytest -q workers/kernel/tests/test_time_skipping.py -m integration
```

首次运行需要下载官方 test-server binary。CI 在 Linux x64 runner 上使用 `NEXWEAVE_TEMPORAL_TEST_SERVER_CACHE` 指定下载目录并以独立 job 执行；2026-08-25 本地与 GitHub Actions run `32808198635` 均已取得真实通过结果。

## 7. 迁移与回滚

- 正常升级：`alembic upgrade head`，M2 head 为 `0003_m2_temporal_kernel`；
- 禁止在活动开发、共享或生产数据库运行 `make migration-check`，因为它会降级到 base；
- downgrade 仅允许在专门创建的一次性数据库验证，先解析并确认精确数据库名；
- M2 回滚会移除任务投影表，Temporal 历史仍在；生产回滚必须先停止 M2 创建流量、保留数据库备份并制定前向恢复/历史兼容计划；
- 不得修改 `0001`、`0002` 或已验收的 `0003` 历史文件来处理新问题，后续只能新增迁移。

## 8. 停止

```bash
make dev-down
```

该命令不删除命名卷。任何删除卷、数据库或 Temporal 历史的操作都不属于本手册默认授权范围。

## 9. 已知条件项

- 本地 Compose 不构成生产 HA、DR、保留策略、升级或容量认证；
- 远程 CI 与双架构 SBOM/CVE/Cosign 已由 run `32808198635` 验证；生产部署仍须按目标环境重新验证 OIDC、Secret、HTTPS、HA/DR 与容量；
- M3 Source/解析、M4 Schema、M5 真实 Compile、M6 Review、M7 Release 等业务仍未实现。
