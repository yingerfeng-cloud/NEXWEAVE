# ADR-0019: M1 身份、授权、空间与托管对象基础

- Status: Accepted
- Date: 2026-08-24
- Approval basis: 用户正式下发 M1 任务书 + ADR-0013/0015/0016/0018
- Decision owners: 产品负责人、架构负责人、安全负责人
- Related: NXW-SPACE-001, NXW-SPACE-002, NXW-ADMIN-001, NXW-NFR-SEC-001, NXW-NFR-SEC-003

## Context

M1 首次把 M0 冻结的租户、身份、权限、空间、审计、Outbox 与对象存储边界变成真实业务能力。若身份声明、角色作用域、空间状态、并发、幂等和对象上传在各接口自行解释，会形成跨租户泄漏、静默覆盖和不可对账的审计事实。

## Decision

### 身份与授权

1. API 只接受经过 `IdentityProviderPort` 验证的 Bearer token。生产适配器验证 OIDC issuer、signature、audience、expiry 和 subject；本地开发适配器使用独立 issuer/audience 和服务端签名令牌，默认只在 development 环境启用。
2. 统一 Principal 至少包含 actor type/id、tenant、subject、audience、平台角色、空间角色、密级许可与 token ID。未经验证的 tenant/role header 不参与授权。
3. 授权为默认拒绝的 RBAC + ABAC：基础角色映射动作，资源事实再按 tenant、space、成员状态、对象状态、密级和服务令牌 audience 收窄。跨租户、跨空间、撤销成员和密级拒绝均记录 append-only AuditLog。
4. `SpaceMember` 是可审计的授权聚合，主体可以是 USER 或 SERVICE；授权更新递增策略版本，撤销保留记录并使后续访问立即失败。平台角色不自动转化为知识审核/发布权限。

### 空间、配置与版本

5. M1 的 `KnowledgeSpace` 使用 `ACTIVE/ARCHIVED` 生命周期，与已验收迁移一致。归档是软归档且不可物理删除；归档空间只允许管理员/审计读取和显式恢复之外的后续受控动作，本 M1 不实现恢复命令。
6. 可变资源使用单调递增 `version`、强 ETag 和 `If-Match`；所有产生副作用的 POST/PATCH/DELETE 接受 `Idempotency-Key`。同 key/同规范请求返回原响应，同 key/不同请求返回 `IDEMPOTENCY_KEY_REUSED`。
7. `ModelProfile`、`PromptVersion` 和 `ConnectorDefinition` 在 M1 只提供治理配置与版本事实：凭据只保存 Secret Provider 引用；PromptVersion 追加式；ConnectorDefinition 不执行外部同步；模型调用与 Connector 运行仍属于后续 Milestone。

### 托管对象与扫描

8. M1 新增 Provider-neutral `ObjectStoragePort`、受控上传会话和 `ManagedObject` 元数据，用于验证真实 RustFS/S3 写入、checksum、条件写、下载重新授权和扫描门禁。它不是 `SourceDocument/SourceVersion`，不得作为 Evidence 或正式知识；M3 仍按 ADR-0018 创建 Raw/SourceVersion 聚合。
9. M1 托管对象 key 为 `managed/v1/{tenant_id}/{space_id}/{upload_session_id}/{sha256}`，原文件名不进入 key。上传会话 ID 在会话创建后不可变，因而可作为条件创建的稳定业务锚点；服务端重新计算 SHA-256、size 和 content type，数据库保存对象版本 ID。
10. 扫描状态为 `PENDING/CLEAN/INFECTED/FAILED`。M1 可使用明确标识的 Stub Scanner，但上传完成不能绕过状态；只有 `CLEAN` 对象可下载。真实恶意文件扫描 Activity 由 M3 SourceIngestion 实现。

### 事务、事件与可观测性

11. 身份、空间、成员、治理配置和托管对象写入在同一 PostgreSQL 事务中写 AuditLog、OutboxEvent 与 IdempotencyRecord。M1 产生空间、成员、用户、服务身份、模型配置、Prompt 版本、Connector 定义和托管对象的版本化事件事实；M1 只写 transactional Outbox，不声称已运行 Broker。
12. Trace context 支持 W3C `traceparent` 并生成/回传 `trace_id`；Web/API/DB/ObjectStorage 的日志、审计和指标使用同一 trace/correlation 信息。遥测内容不得包含 token、凭据或文件正文。

### 数据库隔离纵深

13. M1 的租户/空间隔离权威由服务端授权、强制 tenant/space 查询条件和复合外键共同实现。PostgreSQL RLS 在 M1 不启用：连接池事务级 session context、迁移/后台任务 bypass 和运维恢复策略尚未具备可验证证据；在这些条件完成前启用 RLS 会产生伪安全保证。RLS 可作为后续纵深防御，但不得替代应用授权，也不得把当前实现表述为数据库 RLS 隔离。

## Consequences

- M1 能形成空间创建、成员授权/撤销、归档和托管对象上传/下载的真实前后端闭环，并用统一授权与审计阻断越权。
- 本地开发登录可复现且不绑定生产 IAM；生产部署必须配置可信 OIDC issuer/audience，development 签发端点不得启用。
- ManagedObject 是对象存储基础设施验证对象，不提前冒充 M3 Raw/SourceVersion；后续 Source 模块复用 Port 和校验能力，但创建自己的业务聚合与 Workflow。
- PostgreSQL 方言仍只存在迁移/Adapter；domain/contracts/application 不依赖 SQLAlchemy、FastAPI、OIDC 或 S3 SDK。

## Compatibility and migration

M1 通过新的 `0002_m1_*` 迁移扩展 M0，不修改 `0001_m0`。API/事件/数据库字段的破坏性变化必须新增 ADR 与迁移；历史 AuditLog、Outbox、PromptVersion 和已验证对象不原地改写。

## Validation

- 领域与权限单元测试覆盖默认拒绝、租户/空间/密级、归档、撤销与非法并发；
- 契约测试覆盖 OpenAPI、事件 payload、SDK 基础和 Problem Details；
- 真实 PostgreSQL 验证 migration upgrade/down/up、复合外键、append-only 审计和事务 Outbox；
- 真实 RustFS 验证条件写、checksum、同 key 不覆盖、短期下载授权和扫描状态；
- E2E 验证登录、创建空间、授权成员、撤销权限、归档与审计查询；前端不以按钮隐藏代替服务端授权。
