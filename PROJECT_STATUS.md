# NEXWEAVE Project Status

- Current Release: R1（M0—M9）
- Current Milestone: M0 formally accepted; awaiting separate M1 dispatch
- Business implementation: Not started
- Git repository: Initialized locally
- Git baseline commit: Not created; no configured `user.name` / `user.email`
- M0: Explicitly dispatched by the user on 2026-08-23

## M-1 result

治理、资料归档、产品/架构/领域/数据/API/事件/Workflow/Pack/GridCrew/安全/质量/需求追踪、ADR 和 Spike 基线已建立。用户于 2026-08-23 正式验收通过 M-1。开放问题和 Proposed ADR 作为 M0 评审输入保留，不代表已被静默批准。

## M0 scope

- 冻结终局架构、公共契约、状态/版本/权限/错误/事件/幂等边界；
- 建立 Python/TypeScript Monorepo、最小健康检查 API/Web/Worker、基础迁移、Compose、CI 与测试；
- 仅建立通用身份、空间、审计、Outbox、配置和版本骨架，不建立知识业务表或业务 API；
- 继续保持高保真原型为静态参考，不把 Mock 或固定 JSON 冒充业务功能。

## M0 verification status

- 本地 format、lint、typecheck、Python 单元/契约/架构测试、Web 测试与生产构建通过；
- Python 与 JavaScript 生产依赖审计均为零已知漏洞，Secret scan 与 Compose 配置解析通过；
- `PlatformHealthWorkflow` 已在 Temporal 官方测试服务上真实执行通过；
- 用户于 2026-08-24 批准对象存储完整切换为 RustFS；ADR-0017、活动架构、Compose、健康检查和开发配置已同步，不保留旧 Provider 回退；
- RustFS 官方 Quay `1.0.0-rc.3` 多架构 digest 已核实，Apple Silicon 原生镜像成功拉取并通过真实 Compose `Healthy` 与宿主 `/health` 验证；
- 用户将 Veee 调整为全局模式后，pgvector、Redis、Temporal、Python、Node、Nginx 官方镜像均已成功拉取，API/Worker/Web 项目镜像构建成功；Docker Hub 原 P0 已解除，但首次认证请求仍出现过一次 IPv6 超时，需继续观察稳定性；
- Temporal 1.29.6 动态配置已改用镜像实际提供的 `config/dynamicconfig/docker.yaml`；Compose 健康检查、API 依赖探测和真实 Worker Workflow 均通过；
- Web 已改用完整非 root Nginx 主配置，健康检查固定到实际 IPv4 回环监听地址；`make dev-up` 已使 PostgreSQL、Redis、RustFS、Temporal、API、Worker、Web 全部启动并通过健康等待；
- `make verify` 已通过 Web → API → PostgreSQL/Redis/RustFS/Temporal → Worker 的真实链路；`make migration-check` 已通过基础迁移升级、回滚和再次升级；
- 当前本地 P0 为零。GitHub CI、容器签名/SBOM/漏洞扫描仍无外部或完整回执，继续作为 P1 跟踪，不得因验收而删除或伪报完成；
- 用户于 2026-08-24 在已知上述 P1 遗留的前提下正式验收通过 M0；M1 仍须用户另行明确下发。

## Hard boundaries

- 当前没有 Source、Schema、Compile、Review、Release、Query、GridCrew 等业务功能实现；
- 高保真原型仍是静态演示，不是已完成功能；
- 未提供合规脱敏 RCA 试点资料；
- 未进入 M1 或后续 Milestone；M0 已验收，当前停止并等待下一阶段明确指令。
