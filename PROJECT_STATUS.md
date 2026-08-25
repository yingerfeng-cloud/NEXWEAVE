# NEXWEAVE Project Status

- Current Release: R1（M0—M9）
- Current Milestone: M2 implementation complete and stopped; awaiting user acceptance
- Business implementation: M1 accepted; M2 Temporal workflow kernel and task center implemented within the Stub boundary
- Git repository: `https://github.com/yingerfeng-cloud/NEXWEAVE.git`, local `main` preserves the remote initial commit without force-push
- Git baseline before the M1/M2 delivery commit: `727811f`; the user authorized and pushed the M1/M2 delivery and CI closeout on 2026-08-25. Functional gate commit `ddbcc6e` is on `origin/main` and GitHub Actions run `32808198635` passed
- M0: Explicitly dispatched by the user on 2026-08-23
- M1: Explicitly dispatched by the user on 2026-08-24
- M1: Formally accepted by the user on 2026-08-24
- M2: Explicitly dispatched by the user on 2026-08-24

## M2 implementation result

- Dedicated `nexweave-dev` Temporal namespace, separate Workflow/Activity task queues and a non-root kernel Worker now run the seven named Workflow definitions;
- Stable business/Workflow/Run mapping, Update/Signal control, durable approval wait, timeout escalation, Activity timeout/retry/heartbeat, cancellation compensation and duplicate-command handling are implemented without direct Workflow I/O;
- PostgreSQL `WorkflowTask`, `WorkflowStep` and append-only `WorkflowTaskEvent` projections, audit/Outbox, lag indication and Temporal reconciliation/repair are exposed through authenticated APIs and typed SDKs;
- The Web task center is driven by real APIs and supports list/detail/steps/logs/actions, deep links, refresh recovery and truthful M2 Stub boundaries;
- Real Compose verification passed all seven Workflow types, transient retry, approval, pause/resume, cancellation compensation, duplicate Update, projection repair, Worker restart and replay; isolated PostgreSQL `base → head → base → head` migration verification passed;
- The official Temporal SDK time-skipping test now runs as an independent Linux x64 CI gate; local execution passed and the remote `temporal-time-skipping` job passed in run `32808198635`;
- GitHub Actions run `32808198635` passed all eight quality, time-skipping, Compose integration, four application-image and RustFS approval jobs. Dual-architecture SBOM/CVE evidence and Cosign signature verification were uploaded successfully;
- M2 is stopped awaiting user acceptance. M3 Source/parse work has not been dispatched or started.

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
- RustFS SPK-004 已在固定真实镜像上通过 S3 子集、条件写、版本、鉴权、multipart、生命周期、重启与逻辑备份恢复；对象 key、状态、补偿和供应链规则由 ADR-0018 冻结；
- API、Worker、Web、RustFS 镜像本地复扫的可修复 HIGH/CRITICAL 均为 0；主分支 CI 对四类镜像构建/验证 amd64 与 arm64、生成 CycloneDX/CVE artifacts 并以 GitHub OIDC/Cosign 签名不可变 digest；
- GitHub Actions run `32702688049` 对提交 `e03efd9` 的 quality、Compose integration、API/Worker/Web images、RustFS approval image 六个 job 全部成功；外部 CI、容器供应链与 SPK-004 的 M0 P1 收尾已闭环；
- 当前 M0 P0/P1 阻塞均为零。用户于 2026-08-24 已正式验收通过 M0，并于同日正式下发 M1。

## M1 implementation result

- OIDC-compatible/local development identity、服务身份、audience 校验、默认拒绝 RBAC+ABAC 和 tenant/space/classification 隔离已实现；
- KnowledgeSpace 创建/编辑/归档、成员授权/撤销、治理配置、审计/Outbox/幂等、OpenTelemetry 和受控 RustFS 对象链路已形成真实 API/DB 闭环；
- Web 已实现登录态、空间恢复、16 个深链接路由、权限守卫、空间与管理真实页面；后续模块只陈述边界且无 Mock；
- `0002_m1_platform_services` 真实 PostgreSQL 升级/回滚/再升级通过；最终 Compose 七服务均运行，六个带 healthcheck 的服务为 healthy，Worker Workflow 通过，真实 E2E 两次通过；
- `make check` 通过 Python 28 项、契约 14 项、Web 5 项及 format/lint/typecheck/SDK/build；Secret/SCA/Compose/diff 门禁通过；
- M1 验收时独立 Temporal SDK time-skipping 下载未取得结果；该历史披露已在 M2 收尾中由本地真实通过及远程独立门禁关闭，不改变 M1 无长业务 Workflow 的验收边界；
- M1 无新增 P0。远程 CI 与镜像供应链重跑已由 run `32808198635` 关闭；P1 保留生产 OIDC/Secret Provider/HTTPS 部署联调，P2 保留 OTel contrib `0.65b0` 兼容观察和后续 RLS 纵深评估。

## Hard boundaries

- 当前没有 Source/parse、Schema、真实 Compile、Review 业务对象、Release、Query、GridCrew 等后续业务功能实现；M2 同名 Workflow 仅为可靠内核 Stub；
- 高保真原型仍是静态演示，不是已完成功能；
- 未提供合规脱敏 RCA 试点资料；
- M2 已完成并停止；仍不得提前实现 M3 的 Source/解析或 M4+ 的 Schema、真实 Compile、Review、Release、Query、GridCrew、RCA 业务。
