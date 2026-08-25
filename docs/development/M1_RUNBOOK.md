# M1 运行与使用手册

## 本地启动

前置条件与 M0 相同：Docker Desktop/Compose、Python 3.12、Node 22.12+、pnpm 11.19。执行：

```bash
make dev-up
```

命令只在缺少时创建权限为 `0600` 的忽略文件 `.env`，生成本地凭据，构建镜像、执行 Alembic 到 head，并等待 PostgreSQL、Redis、RustFS、Temporal、API、Worker、Web 就绪；不会覆盖已有 `.env`。

- Web：`http://localhost:8080`
- API 文档：`http://localhost:8000/api/docs`
- 就绪检查：`http://localhost:8000/api/v1/health/ready`
- RustFS 控制台：`http://localhost:9001`（凭据仅在忽略的 `.env`）

Web 登录页默认使用合成身份 `local-admin`。本地签发接口仅在 development 且 `NEXWEAVE_LOCAL_DEV_IDENTITY_ENABLED=true` 时存在；token 保存在浏览器 `sessionStorage`，当前空间 ID 保存在 `localStorage`，深链接、刷新和浏览器返回可恢复。

## M1 可用范围

- 总览：真实知识空间和审计摘要；
- 知识空间：创建、编辑、成员授权/撤销、软归档；
- 系统管理：用户、角色、服务身份、模型配置、Prompt 版本、Connector 定义和审计查询；
- API/SDK：受控托管对象上传、checksum/扫描状态、元数据和重新授权下载；
- 其余 13 个后续知识模块保留可深链接路由，但只说明阶段边界，不返回 Mock 数据。

`ManagedObject` 仅验证 M1 对象存储基础，不是 Source/SourceVersion，不能用于 Evidence、Compile 或 Release。M1 扫描器是明确标识的策略 Stub（包含 EICAR 特征识别）；只有 `CLEAN` 对象可下载，生产资料接入必须等待 M3 的真实扫描 Activity。

## 管理员操作原则

- 创建/变更动作由 UI 自动携带幂等键；空间编辑和归档必须基于最新 ETag，冲突后重新读取再操作；
- 用户/服务身份必须先存在，才能授予空间角色；撤销保留审计事实并即时失效；
- 服务身份的 tenant 角色固定为 `service`，必须同时具有 `nexweave-api` audience 和显式空间成员角色；
- ModelProfile/ServiceIdentity 的凭据字段只允许 Secret Provider 引用，不接受真实密钥正文；
- 外部托管模型 Profile 不得把最大密级配置为 `HIGHLY_RESTRICTED`；M1 不执行模型或 Connector。

## 生产 OIDC 与 Secret Provider

非 development 环境必须设置：

```text
NEXWEAVE_IDENTITY_PROVIDER=oidc
NEXWEAVE_OIDC_ISSUER=https://<trusted-issuer>
NEXWEAVE_OIDC_JWKS_URL=https://<trusted-issuer>/<jwks>
NEXWEAVE_OIDC_AUDIENCE=nexweave-api
NEXWEAVE_OIDC_ALGORITHMS=RS256,ES256
NEXWEAVE_LOCAL_DEV_IDENTITY_ENABLED=false
NEXWEAVE_SECRET_PROVIDER=<external-provider-name>
```

OIDC token 必须包含标准 `iss/sub/aud/iat/exp/jti` 和 `nexweave_actor_type`、`nexweave_actor_id`、`nexweave_tenant_id`；可选 `nexweave_clearance` 默认为 `INTERNAL`。角色由 NEXWEAVE 数据库授权事实解析，不信任 token 自报角色。生产 issuer/JWKS 必须为 HTTPS，算法只能来自配置的非对称 allowlist。

M1 仅冻结 Secret Provider 引用边界，未集成具体厂商；非 development 若仍使用 `local-env-m1-only` 会拒绝启动。HTTPS 终止、生产 IAM 映射与外部 Secret Provider 属于部署集成，不由本地 Compose 冒充。

## 验证与迁移

```bash
make check PYTHON=.venv/bin/python
make verify PYTHON=.venv/bin/python
make migration-check
```

`make verify` 使用合成数据验证 Web 深链接、认证、跨租户/空间拒绝、成员撤销、空间归档、真实 PostgreSQL Audit/Outbox、真实 RustFS 条件写/checksum/扫描/下载和真实 Temporal health Workflow。`make migration-check` 会在本地一次性数据库执行 `base → head → base → head`，会删除本地 M1/M0 表，禁止对共享或生产数据库执行。

Python/TypeScript SDK 使用说明见 `packages/sdk/README.md`，公共契约以提交的 OpenAPI/JSON Schema 为准。

## 诊断与停止

- `/api/v1/config/diagnostics` 只返回脱敏配置；
- 每个 API 响应返回 `X-Trace-ID`，客户端可提交 W3C `traceparent`，AuditLog 使用同一 trace ID；
- `make dev-logs` 查看 API/Worker/Web 结构化日志；日志和 telemetry 不应包含 token、凭据或对象正文；
- `make dev-down` 停止并保留卷；只有明确要销毁本地合成数据时才使用带 volumes 的 Compose down。

## 阶段边界

M1 不包含 Source、Schema、Compile、Wiki、Claim/Evidence、Graph、Conflict、Review、Quality、Release、Query、Domain Pack、GridCrew 或真实 Connector/模型执行。不得把占位路由、ManagedObject 或 Temporal health Workflow当作这些业务能力。
