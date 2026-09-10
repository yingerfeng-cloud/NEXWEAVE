# NEXWEAVE M4 执行与验收报告

## 1. 总体结论

- 阶段结论：**正式验收通过**。M4-0、正式实施、独立审查、缺陷修复、真实回归和用户验收已于 2026-08-30 完成。
- 用户验收边界：用户已明确同意 M4 验收；该验收不自动授权或下发 M5。
- Git 状态：工作区保留未提交交付物；用户未授权 commit/push，未伪造远程 CI 或供应链回执。
- P0：0。独立审查暴露的两个真实集成 P0 均已修复并重跑全链。

## 2. 实际完成范围

1. M4-0：ADR-0023 冻结 lower-case namespaced stable key、JSON-only `RFC8785-JCS/1`、Ed25519 trust/revocation、preview-only migration DSL 和声明式 UI allowlist，并同步 Open Questions 与公共契约。
2. Schema/Semantic Model：实现 SchemaDefinition、不可变 SchemaVersion、类型、属性、多父 DAG、关系、术语、ConceptMapping、模板、Lint/Evaluation/UI 声明和 CompositionReport；未新增 OntologyVersion 或第二权威。
3. 组合与迁移：实现精确 PackVersion/checksum 输入、确定性拓扑组合、引用/冲突/循环/继承/端点/映射校验、兼容分类、影响清单和白名单迁移预览；M4 不执行实例迁移。
4. Pack 安全与生命周期：实现签名注册、命名空间归属、信任根、离线签名撤销、依赖解析、安装、升级、禁用、回滚、审计与 Outbox；安装只生成 DRAFT 候选。
5. Workflow/API/SDK/UI：新增 `nexweave.domain-pack-install.v2` 和可重试 Activities，保留 v1 replay；交付 typed OpenAPI/JSON Schema/events、Python/TypeScript SDK、Schema Studio 和 Pack Center。
6. Fixture：交付 core、equipment-rca、maintenance 三个 test-only 签名声明 Pack；Equipment/RCA 概念未进入平台核心，不包含自动根因诊断。
7. 非目标：未实现 M5 Compile、知识 Entity/Relation/Claim/Evidence、Review、Release、Query、GridCrew、真实 Connector/Model 调用或自动 RCA。

## 3. 主要变更路径

- 治理与契约：`docs/architecture/adr/ADR-0022*`、`ADR-0023*`、`SEMANTIC_MODEL_BASELINE.md`、各 architecture baseline、`OPEN_QUESTIONS.md`、M4 任务书、追踪矩阵。
- 领域与公共契约：`packages/domain/src/nexweave_domain/semantic.py`、`packages/contracts/src/nexweave_contracts/{semantic,domain_pack,semantic_events}.py`、生成 JSON Schema/OpenAPI。
- 数据与服务：`migrations/versions/0005_m4_semantic_model.py`、`apps/api/src/nexweave_api/{semantic_repository,semantic_routes}.py`、API 注册与 RBAC。
- 工作流：`workers/kernel/src/nexweave_worker_kernel/{workflows,activities,main}.py` 及 v1/v2 replay 测试。
- 客户端与 UI：Python/TypeScript SDK、`SchemaStudio.tsx`、`PackCenter.tsx`、Web API/types/tests。
- Fixture 与验收：`domain-packs/fixtures/`、`scripts/verify_m4.py`、增强后的 migration checker、CI/Make targets。

## 4. 公共契约、版本与历史

- Stable key：小写 ASCII `namespace/local-name`，显示名不参与身份；保留命名空间只有平台管理员可登记。
- Pack：v1alpha1 JSON-only，canonical descriptor 排除 signature value 后签名；content/path/checksum 和资源预算均在验证前限制。
- SchemaVersion：`DRAFT→TESTING→PUBLISHED→DEPRECATED`；PUBLISHED 内容由数据库 trigger 阻止原地修改或删除。
- PackVersion/CompositionReport/semantic facts：append-only；SchemaVersion 固化算法、composition checksum 和 exact PackVersion/checksum 顺序。
- Workflow：M4 使用 `nexweave.domain-pack-install.v2`；M2 `v1` 不改义且真实 replay 通过。
- Event：`io.nexweave.schema.published.v1` 与 `io.nexweave.pack.installed.v1` 只携带最小固定引用；Pack installed 不代表 Schema published。

## 5. 真实验收证据

### 5.1 静态、单元、契约与 Web

- Ruff format/check：通过；strict mypy 66 source files：通过。
- Python：94 passed，5 integration deselected；M4 Temporal integration 单独 1 passed。
- Contract/OpenAPI committed snapshots：22 passed；生成物与应用 OpenAPI 一致。
- Web：Prettier、ESLint、TypeScript、production build 通过；13 tests passed，含 Schema 校验/发布分离和 Pack 候选不自动发布。
- `git diff --check`、Compose config、架构依赖边界：通过。

### 5.2 PostgreSQL 与 Compose

- 开发数据库 head：`0005_m4`。
- 一次性数据库：`0001→0002→0003→0004→0005→0004→0005` 通过，M4 表/trigger/复合外键有效，M0—M3 sentinel 数据保留。
- Compose：PostgreSQL、Redis、RustFS、Temporal、ClamAV、Parser sandbox、API、Web 和 Workers 均通过健康/实际调用验证。
- M0、M1、M2、M3 四个真实回归程序全部通过；M3 仍如实声明无真实 OCR Provider。

### 5.3 M4 纵向链

- 验收空间：`m4-e2e-bd30d184db`。
- SchemaDefinition：`01a04ff1-99fc-78bc-84eb-8af2028a3eda`。
- PUBLISHED SchemaVersion：`01a04ff1-9a49-7b29-94a6-f4275870868e`，语义版本 `0.2.0`。
- composition checksum：`sha256:a71aca50382c18ca54c12f196337d7939ab49bcc35812685548d38a9c85f9931`。
- core Pack checksum：`sha256:c31aa2b7a6986f03779f3f9a0594e7c5d675955685e9dd4af07f9e8ac86cb224`。
- equipment-rca 1.0 checksum：`sha256:e193c4f3b0f0aaddef87a591bdf9565cc6a662e8b48463df05f8443bff7d1618`。
- maintenance 1.0 checksum：`sha256:59dcc844537ee30b23e4111fdc2c88693ac04ea1c5718ee4fe80ff6658e6b22e`。
- 安装 Workflow `pack-install/.../install:...:0.2.0` 终态 ACTIVE；upgrade/disable/rollback 分别产生显式历史记录，最终 rollback 终态 ROLLED_BACK。
- 真实拒绝：篡改签名 403、撤销后 Pack 不再列为可安装、跨空间 Schema 引用 404；安装候选保持 DRAFT，独立 publisher 身份完成 publish。
- 真实失败演练：动态签名 Pack 引用不存在依赖，Workflow 在重试/分类后进入 FAILED，Installation 投影为 FAILED，审计以 `PACK_DEPENDENCY_CONFLICT` 记录且不泄漏 Pack 内容。
- 收口后连续两次运行 `scripts/verify_m4.py` 均通过；撤销演练使用每次隔离的动态签名目标，证明验收脚本可重复执行且不会污染后续可安装 Pack。

## 6. 独立审查与修复

独立于首次实现顺序执行了完整 diff、契约漂移、依赖方向、权限、迁移、历史兼容、安全输入和真实 E2E 复核。发现并修复：

1. Pack 安装路由把 UUID 直接传入 Workflow projection JSON，真实 API 返回 500；现统一投影为稳定字符串。
2. Pack composition 已生成 append-only CompositionReport，validate 再插入相同 input 违反唯一约束；现复用精确不可变报告，仅推进 Schema 状态并保持审计。

修复后重新构建 API，M4 E2E、Temporal replay、M0—M3 回归和全部静态/单元/契约/Web 门禁通过。

## 7. 安全、权限、审计与供应链

- Pack 声明拒绝路径逃逸、绝对路径、脚本/HTML/CSS、远程 URL/include、宏、表达式、事件 handler 和不在 UI allowlist 的字段。
- Ed25519 key、namespace ownership、validity、artifact checksum 和 signed revocation 都在写数据库前验证；撤销不删除历史。
- `schema.read/edit/validate/publish` 与 `pack.read/install/rollback` 分权；安装者不自动取得发布权。跨 tenant/space 由 composite FK、repository scope 和 API authorization 共同阻断。
- M4 审计实测至少产生 32 条 DomainPack 资源审计和 7 条 SchemaVersion 审计；业务写与 Outbox 同事务。
- M4 无新增依赖；复用锁定 `cryptography==50.0.0`。Secret scan、`pip check` 和本地 Python/JavaScript production dependency audit 通过。
- 未执行远程 multi-architecture build/SBOM/CVE/Cosign promotion，因为没有 commit/push 授权；不伪称远程结果。既有 M3 已验收供应链证据保持有效，M4 代码的远程 promotion 仍需未来获授权提交后由 CI 产生。

## 8. 需求追踪与风险

- `NXW-SCHEMA-001/002`、`NXW-PACK-001/002`、`NXW-SEMANTIC-001/002` 更新为 M4 VERIFIED；`NXW-SEMANTIC-003/004` 保持 M5+ baseline，不提前实现。
- P0：无。
- P1：M4 代码尚无远程 CI/promotion 回执（无 commit/push 授权）；生产 OIDC/Secret Provider、HA/DR 和对象存储 RC 风险沿既有后续门禁跟踪。
- P2：专业图形本体编辑、RDF/OWL 往返和实例迁移执行均为明确非目标；若未来需要必须新 ADR。

## 9. 停止声明

已停止在正式验收通过的 **M4**。未创建 M5 对象、迁移、API、Workflow、UI 或任务书实施变更；下一 Milestone 必须等待用户单独明确下发。
