# NEXWEAVE M1 执行结果

## 1. 总体结论

- 阶段：**通过（用户于 2026-08-24 正式验收）**。M1 平台基础、身份权限、空间、治理配置、托管对象、审计/Outbox、可观测性与 Web 管理闭环均已形成真实、可测试、可迁移的纵向能力。
- 是否满足进入下一阶段条件：**是**；用户已于 2026-08-24 明确下发 M2。
- Git 基线：M1 执行/验收时 HEAD 为 `727811f` 且变更未提交；用户于 2026-08-25 随后授权使用仓库既有 Git 身份提交并 push 合并 M1/M2 交付，功能门禁提交 `ddbcc6e` 与 run `32808198635` 已取得远程全绿回执。
- 阶段边界：没有实现 Source、Schema、Compile、Wiki、Claim/Evidence、Graph、Conflict、Review、Quality、Release、Query、Domain Pack、GridCrew、真实 Connector/模型执行或 RCA 功能。

## 2. 实际完成范围

### 身份与权限

- 实现 `IdentityProviderPort`、独立 local development provider 和厂商无关 OIDC adapter；生产校验 issuer、JWKS signature、audience、expiry、subject、jti，并使用配置化非对称算法 allowlist；
- 实现 User/ServiceIdentity、tenant roles、space membership、service audience 与四级密级；token 自报角色不授予权限，角色从数据库授权事实解析；
- 实现默认拒绝 RBAC+ABAC，联合 tenant、space membership、资源归档状态、classification clearance 与 service audience；跨租户、跨空间、撤销后访问和密级拒绝均由服务端执行并记录审计；
- 服务身份 tenant 角色固定为 `service`，必须获得显式空间角色，不能继承人类所有者权限。

### 核心领域与数据库

- 实现 `KnowledgeSpace`（ACTIVE/ARCHIVED）、`SpaceMember`（ACTIVE/REVOKED）、ModelProfile、追加式 PromptVersion、ConnectorDefinition、AuditLog、OutboxEvent 和 IdempotencyRecord；
- 空间创建/编辑/归档使用 UUIDv7、幂等键、强 ETag/If-Match、单调版本和软归档；核心事实没有物理删除 API；
- 身份、空间、成员、治理配置、托管对象写入在同一 PostgreSQL 事务中记录 AuditLog、Outbox 和幂等结果；
- M1 隔离由应用授权、强制 tenant/space 查询和复合外键共同承担；未用未经运维验证的 RLS 冒充纵深隔离。

### 文件与对象存储

- 实现 Provider-neutral `ObjectStoragePort`/`MalwareScannerPort`、RustFS S3 adapter、受控上传会话、代理上传和重新授权下载；
- 对象 key 不含原文件名，服务端重算 SHA-256、size 和 content type；条件创建防止同 key 静默覆盖，数据库保存 RustFS version ID；
- 扫描状态完整保留，只有 `CLEAN` 可下载；M1 策略 Stub 可识别 EICAR 特征，不绕过状态；
- `ManagedObject` 明确不是 SourceDocument/SourceVersion，不能作为 Evidence 或 Release 输入。

### 前端与管理

- 实现登录态恢复、16 个深链接路由、浏览器返回、刷新恢复、空间切换、管理权限守卫和页面级错误边界；
- 实现真实 API 驱动的总览、空间创建/编辑/归档、成员授权/撤销、用户、角色、模型配置、Prompt 版本、Connector 定义与审计页面；
- 列表具备加载、空状态、错误和真实重试；后续模块路由只陈述 M1 边界，不展示 Mock/固定 JSON；
- 保持 NEXWEAVE 深色设计语言、响应式布局、语义化控件和键盘可操作基础。

### 可观测性与平台端点

- 接入 OpenTelemetry trace/metric/log、FastAPI/SQLAlchemy/logging instrumentation 和 S3 手工 span/metric；
- Web 生成 W3C `traceparent`，API 回传 `X-Trace-ID` 并在 DB/Audit/Object Storage 链路关联；token、凭据和对象正文不进入 telemetry；
- 保留真实健康、就绪、版本和脱敏配置诊断端点，版本更新为 M1。

### API、事件与 SDK

- 实现 M1 身份、角色、用户、组织、服务身份、空间、成员、治理、审计、上传与对象端点，统一 Bearer/OpenAPI security、RFC 9457 Problem、稳定错误码和 common responses；
- 所有列表统一 `limit/cursor/items/next_cursor`，使用不可变标识作为 continuation anchor，非法/失效游标返回 `INVALID_CURSOR`；
- 生成并提交 M1 OpenAPI 3.1、JSON Schema 和空间/成员/平台实体事件 payload；
- 提供 typed Python async 与 TypeScript SDK 基础，携带 Bearer、traceparent、Idempotency-Key 和 ETag。

## 3. 新增或修改文件

### 根工程与运行（M1 全局门禁；NXW-ADMIN-001/NXW-NFR-SEC-003）

- `.env.example`, `compose.yaml`, `Makefile`, `package.json`, `pyproject.toml`：M1 配置、启动、验证、包边界和统一命令；
- `requirements/runtime.txt`, `requirements/runtime.lock`, `requirements/dev.txt`, `requirements/dev.lock`：OIDC、S3、OTel 等精确依赖锁；
- `apps/api/Dockerfile`, `scripts/bootstrap_env.py`, `scripts/check_migrations.py`, `scripts/verify_m1.py`, `scripts/provision_m1_e2e_tenant.py`：最终镜像、合成环境、迁移与真实 E2E。

### 领域、应用、契约与 SDK（NXW-SPACE-001/002、NXW-ADMIN-001、NXW-ARCH-001）

- `packages/domain/src/nexweave_domain/access.py`, `workspace.py`, `governance.py`, `__init__.py`：RBAC+ABAC、空间/成员聚合和 M1 状态词汇；
- `packages/application/src/nexweave_application/ports.py`, `concurrency.py`, `__init__.py`：身份/对象/扫描 Port 与规范幂等 hash；
- `packages/contracts/src/nexweave_contracts/identity.py`, `workspace.py`, `governance.py`, `objects.py`, `m1_events.py`, `base.py`, `schema_export.py`, `__init__.py`：canonical contracts；
- `packages/contracts/schemas/*.schema.json`, `packages/contracts/openapi/nexweave-platform-v1.openapi.json`：M1 版本化生成物；
- `packages/sdk/python/nexweave_sdk/`, `packages/sdk/typescript/`, `packages/sdk/README.md`：Python/TypeScript SDK 基础。

### API、Web、迁移与测试（NXW-DASH-001、NXW-SPACE-001/002、NXW-ADMIN-001）

- `apps/api/src/nexweave_api/app.py`, `settings.py`, `database.py`, `errors.py`, `identity.py`, `m1_routes.py`, `object_storage.py`, `repository.py`, `telemetry.py`：M1 API 与 adapters；
- `apps/web/src/App.tsx`, `api.ts`, `types.ts`, `styles.css`, `App.test.tsx`：M1 authenticated platform Web；
- `migrations/versions/0002_m1_platform_services.py`：M1 追加迁移和 downgrade；
- `apps/api/tests/test_app.py`, `packages/domain/tests/test_m1_access_workspace.py`, `tests/contract/test_m1_*.py`, `tests/architecture/test_dependency_boundaries.py`, `tests/contract/test_openapi_snapshot.py`：领域、权限、API、Port、契约、SDK、架构和快照测试。

### 架构、治理与使用文档

- `docs/architecture/adr/ADR-0019-m1-identity-workspace-object-foundation.md` 与 ADR index：M1 核心语义、RLS 决策和兼容策略；
- `ARCHITECTURE_BASELINE.md`、API/Event/Data/Domain/State/C4 baselines：同步 M1 已实现边界；
- `docs/governance/DEPENDENCY_BASELINE.md`, `MIGRATION_FIXTURE_STRATEGY.md`, `QUALITY_GATES.md`, `REQUIREMENTS_TRACEABILITY_MATRIX.md`：依赖、迁移、门禁与追踪；
- `docs/development/M1_IMPLEMENTATION_PLAN.md`, `M1_RUNBOOK.md`, 本报告、`docs/INDEX.md`, `PROJECT_STATUS.md`, `OPEN_QUESTIONS.md`, `CHANGELOG.md`, `AGENTS.md`：实施、运行、状态和停止边界。

## 4. 领域对象、API、事件和 Workflow 变更

- 新增领域对象/值：Principal、Role/ROLE_ACTIONS、AuthorizationRequest/Decision、KnowledgeSpace、SpaceMember、Governance/Connector/Scan/Upload 状态；
- 新增 API：`/auth/*`, `/roles`, `/users`, `/organizations`, `/service-identities`, `/spaces*`, `/audit-logs`, `/model-profiles`, `/prompt-versions`, `/connector-definitions`, `/object-uploads*`, `/objects*`；
- 新增事件：`space.created/updated/archived`, `membership.changed`, `user.created`, `service_identity.created`, `model_profile.created`, `prompt_version.created`, `connector_definition.created`, `managed_object.stored` v1；M1 只写 transactional Outbox，不声称已运行 Broker；
- Workflow：没有新增业务 Workflow。M1 没有长任务，继续使用确定性的 `nexweave.platform.health.v1` 验证 Temporal/Worker；
- 兼容性影响：全部为 `/api/v1` additive 路径/可选分页字段和 `0002` 追加迁移；M0 健康端点保持兼容。ManagedObject 不改变 SourceAnchor/Evidence/Release 语义；
- ADR：ADR-0019 Accepted，未修改历史 ADR 或 M0 `0001` 迁移。

## 5. 测试与验证

### 已通过

- `make check PYTHON=.venv/bin/python`：format、Ruff、mypy、ESLint、TypeScript、Prettier、SDK 和 production build 全部通过；Python **28 passed / 1 deselected**，Web **5 passed**，契约子集 **14 passed**；
- `.venv/bin/python scripts/verify_m1.py`：最终镜像与迁移恢复后各通过一次；输出 `Temporal worker health workflow passed` 与完整 Web→认证 API→tenant/space policy→PostgreSQL Audit/Outbox→immutable RustFS object→Temporal Worker 链路通过；
- `docker compose exec -T api python scripts/check_migrations.py`：真实 PostgreSQL `base → head → base → head` 通过；
- 七个 Compose 服务最终均运行，六个带 healthcheck 的服务为 healthy，Worker 真实 Workflow 通过；最终两分钟 API/Worker/Web 日志未发现 ERROR、Traceback 或未处理异常；
- `.venv/bin/python scripts/secret_scan.py`、`.venv/bin/python -m pip check`、`docker compose config --quiet`、`git diff --check`：通过；
- `.venv/bin/python -m pip_audit -r requirements/runtime.txt`、`pnpm audit --prod --audit-level high`：均为 **No known vulnerabilities found**。

### 未完成/不伪造

- M1 验收当时，独立 `.venv/bin/python -m pytest -q -m integration` 需要从 `temporal.download` 下载官方 time-skipping test server；受限网络首次明确失败，获准联网后 90.53 秒仍无输出，人工中止（1 个测试未取得结果）。真实 Compose Temporal server/Worker workflow 已在两次最终 E2E 中通过；当时不把下载项写成成功，后续闭环见本报告 P2 补充。
- M1 验收时按规则未提交或 push；2026-08-25 用户随后明确授权提交并 push，run `32808198635` 的外部 CI、双架构镜像 SBOM/CVE/Cosign 回执已取得。该补充证据不改写 M1 验收时的历史事实。
- 未执行生产 OIDC、外部 Secret Provider、HTTPS ingress、国产浏览器矩阵、HA/DR 或性能认证；它们需要实际部署环境，不以本地配置冒充。

## 6. 数据库与迁移

- 迁移文件：`migrations/versions/0002_m1_platform_services.py`，down revision 为已验收 `0001_m0`；
- 增量：service audience、tenant role、space member/role、idempotency、ModelProfile、PromptVersion、ConnectorDefinition、upload session、ManagedObject，以及 M0 身份/空间/审计/Outbox 字段/约束扩展；
- 回滚验证：真实 PostgreSQL `base → head → base → head` 通过，最终 revision 为 `0002_m1`；
- 数据兼容性：不修改历史迁移；Prompt/Audit/Outbox 追加式，Space 软归档。`DROP INDEX IF EXISTS` 仅用于恢复本地曾出现的同 revision 预验收 schema，不代表允许改写接受后的迁移；
- 迁移影响：验证会销毁一次性本地数据；之后已重启 API 恢复合成开发身份并再次通过 E2E。禁止对共享/生产数据库运行 rollback check；
- RLS：M1 未启用，原因与后续前置证据已记录 ADR-0019；当前隔离测试基于应用授权、查询 scope 和复合 FK。

## 7. 安全、权限、审计与证据检查

- 跨租户与跨空间读取由服务端阻断并写 DENIED Audit；跨租户资源对外返回 404 防枚举；成员撤销后访问立即返回 403；
- authorization 默认拒绝；service audience、角色、成员、资源归档和 classification clearance 均参与决策，前端隐藏不授予权限；
- 空间/成员/身份/治理/对象写入产生 traceable Audit 和 transactional Outbox；E2E 验证空间 create/update/archive 事件数量、拒绝 trace 与审计一致；数据库 trigger 阻止 Audit update；
- Idempotency-Key 相同请求回放、不同请求 hash 返回冲突；ETag stale update 返回 412；规范 hash 已覆盖 UUID/Enum/timezone 值；
- RustFS bucket versioning 开启；直接用同 key/不同 bytes 的条件写被拒绝；checksum/size/type 由服务端验证；感染对象不能下载，正常对象需重新授权且字节精确一致；
- 生产非 development 强制 OIDC HTTPS 和外部 Secret Provider；本地签发端点在生产不可用；数据库只存 credential reference；
- Secret/SCA 通过，遥测与错误响应不泄露 token、密钥、堆栈或正文；
- 未新增/修改 SourceAnchor、Evidence 或 Release 语义。ManagedObject 明确不构成 Raw/Evidence，未用静态 UI 或 LLM 文本冒充证据链。

## 8. 风险与遗留项

### P0

- 无已知 P0；M1 最低验收链路、迁移、权限、对象防覆盖、审计和本地全量门禁均通过。

### P1

- 生产 OIDC claim 映射、外部 Secret Provider 和 HTTPS ingress 需在目标环境联调；本地仅验证严格配置边界；
- M1/M2 合并交付的远程 CI 与双架构应用镜像 SBOM/CVE/Cosign 已由 run `32808198635` 关闭；
- RustFS `1.0.0-rc.3` 的分布式/HA、升级回滚、规模和生产 RPO/RTO 仍按既定 M7/M12 门禁，不由 M1 单节点 E2E关闭。

### P2

- OpenTelemetry contrib instrumentation 为精确锁定的 `0.65b0`，保持 adapter 隔离并持续观察兼容性；
- RLS 仅作为后续纵深选项，需先验证连接池 session context、后台任务 bypass、迁移和恢复运维；
- M1 验收时披露的 Temporal SDK time-skipping 下载未取得结果已在 M2 收尾中由本地与远程独立门禁关闭；
- 国产浏览器矩阵、离线内网交付与无障碍专项认证仍待目标环境；当前仅通过响应式/语义/组件/production build 门禁。

## 9. 需求追踪更新

- 已完成需求 ID：`NXW-SPACE-001`, `NXW-SPACE-002`, `NXW-ADMIN-001`, `NXW-ARCH-001`（M1 持续）；
- 部分完成需求 ID：`NXW-DASH-001`（M1 Space/Audit 概览）、`NXW-NFR-SEC-001`（本地无生产 HTTPS 终止）、`NXW-NFR-SEC-002`（治理策略已实现，真实模型流待 M5）、`NXW-NFR-SEC-003`（业务审计/Secret 引用/SCA 与远程供应链已完成，生产 Secret Provider 待部署）、`NXW-NFR-AUD-001`（M1 模型/Prompt/Connector 可追溯）、`NXW-NFR-COMPAT-001`, `NXW-ARCH-002`；
- 未覆盖需求 ID：M2+ 的 Source、Schema、Compile、Wiki、Claim/Evidence、Graph、Conflict、Review、Quality、Release、Query、Pack、Integration/GridCrew 与知识质量/性能/HA 正式验收项；它们保持 `BASELINED`，没有提前实现或伪造。

## 10. 停止声明

M1 已于 2026-08-24 正式验收；随后仅依据用户明确指令进入 M2，未自行跳过治理门禁。
