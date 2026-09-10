# NEXWEAVE M5 执行结果

## 1. 总体结论

- 阶段：通过（本地技术验收通过，并于 2026-08-30 由用户正式验收；远程全局 CI 未因缺少 commit/push 授权而触发，其风险作为已披露 P1 延续）
- 是否满足进入下一阶段条件：是；但 M6 尚未下发，不得自行进入
- Git 基线：工作区未提交；遵循用户未授权 commit/push 和不得覆盖既有 M4 修改的约束

## 2. 实际完成范围

- M5-0：新增 Accepted ADR-0024，冻结固定 Compile 输入、Model Gateway、安全路由、稳定身份、Wiki 保护区与 v1/v2 兼容。
- Model Gateway：新增 provider-neutral Port、结构化输出/embedding 能力边界、预算、checksum、units、latency、cost 和 ModelInvocation 审计事实；本地验收 Provider 明确无网络且不冒充外部 LLM。
- 编译流水线：实现 Schema stable key 驱动的实体/Claim/Relation 提取、SourceAnchor EvidenceCandidate、跨 Job Claim ConflictCandidate、Evidence 缺失 LintFinding、语义变更候选入口、稳定身份和幂等版本写入。
- Wiki：实现 Page/PageVersion、generated/protected sections、结构化属性、Markdown、版本列表/详情/diff、链接/反链、评论、关注、Evidence 元数据和 ETag 人工新版本编辑。
- Workflow/API/SDK/UI：保留 v1 Stub，新增真实 `knowledge-compile.v2`/Activities；新增 Compile/Wiki API、OpenAPI/JSON Schema/event、Python/TypeScript SDK、真实 Compile Center 与 Wiki Workbench。
- 评测：提供领域/契约/Provider/Workflow/Web 自动化测试和真实 E2E 回归。未定义或伪造业务准确率阈值；OQ-METRIC-001 继续保留。

## 3. 新增或修改文件

- `docs/architecture/adr/ADR-0024-m5-compile-wiki-model-contract.md`：M5 实现级架构决策；NXW-COMPILE/WIKI/SEMANTIC/NFR-SEC。
- `packages/domain/src/nexweave_domain/knowledge.py`：纯领域 Compile/Wiki 规则、稳定 key 和本地确定性编译。
- `packages/application/src/nexweave_application/ports.py`：Model Gateway Port/DTO。
- `packages/contracts/src/nexweave_contracts/compile.py`、生成的 schema/OpenAPI：M5 公共契约。
- `migrations/versions/0006_m5_compile_wiki.py`：M5 additive 数据模型、约束和不可变 trigger。
- `apps/api/src/nexweave_api/model_gateway.py`、`knowledge_repository.py`、`knowledge_routes.py`：Provider adapter、事务服务与 API。
- `workers/kernel/src/nexweave_worker_kernel/{workflows,activities,main}.py`：Compile v2 Workflow/Activity 注册。
- `apps/web/src/{CompileCenter,WikiWorkbench,api,types,App,styles}.tsx|ts|css`：真实编译与 Wiki 工作台。
- `packages/sdk/python/nexweave_sdk/client.py`、`packages/sdk/typescript/src/client.ts`：M5 typed SDK。
- `.env.example`、`compose.yaml`、API settings：统一 M5 构建版本 `0.6.0-m5`，避免旧本地环境值产生矛盾版本回执。
- `scripts/verify_m5.py`、M5 domain/contract/API/Workflow tests：自动化与真实验收。
- 根基线、架构/API/数据/事件/Workflow/权限文档、质量门禁、需求追踪、CHANGELOG、状态、任务书与本 Runbook/报告：M5 治理收口。

## 4. 领域对象、API、事件和 Workflow 变更

- 新增：CompileJob/Source/Step、ModelInvocation、KnowledgeEntity/Version、CandidateRelation、Claim/Evidence/Conflict/Lint/SemanticChangeProposal、WikiPage/Version/Link/Comment/Follow。
- API：Compile create/list/detail；Entity list；Wiki list/detail/edit/version/diff/comment/follow。写入具 Idempotency-Key/ETag、授权与审计；失败重试形成新 Job。
- 事件：`io.nexweave.compile.completed.v1` 与 canonical JSON Schema，事务 Outbox 同步提交。
- Workflow：v1 历史定义不改；v2 固定输入并只通过 Activity 访问模型/数据库，Activity 具 timeout/heartbeat/retry/fail projection。
- 兼容性影响：仅 additive API/schema/table；未修改 `0001`—`0005` 历史迁移；M0—M4 sentinel 在 down/up 验证中保留。
- ADR：ADR-0024 Accepted。

## 5. 测试与验证

- `.venv/bin/ruff check .`：通过。
- `.venv/bin/mypy`：71 source files，无问题。
- `NEXWEAVE_TEMPORAL_TEST_ENDPOINT=127.0.0.1:7233 ... .venv/bin/pytest -q`：106 passed。
- OpenAPI/JSON Schema snapshot：2 passed；M5 定向 domain/contract/Provider 测试通过。
- Web Prettier/ESLint/typecheck/test/build：13 tests passed，production build 成功；TypeScript SDK strict check 通过。
- `scripts/verify_m5.py`：真实 Source/Parse→PUBLISHED Schema→Compile v2→ModelInvocation→Entity/Relation/Claim/Evidence/Conflict→Wiki/link/version/protected/comment/follow→审计/Trace/Consumer deny 全链通过。
- Compose 最终运行态：API/Web healthy，Kernel Worker 运行；`/version` 返回 R1/M5/`0.6.0-m5`，`/health/ready` 四项依赖均为 `up`。
- Secret pattern scan：通过。
- 未执行：远程 CI、双架构镜像、SBOM/CVE/Cosign；原因是用户未授权 commit/push，不伪造外部回执。

## 6. 数据库与迁移

- 迁移文件：`0006_m5_compile_wiki.py`，down revision `0005_m4`。
- 回滚验证：一次性数据库真实完成 `0001→0006→0005→0006`。
- 数据兼容性：全部 M5 表/trigger 存在，M0—M4 sentinel 保留；历史迁移未修改，开发库保持 `0006_m5`。

## 7. 安全、权限、审计与证据检查

- 默认拒绝：Consumer 读取 Wiki 草稿真实返回 403；Compile/Wiki 权限由服务端 tenant/space/role/clearance 决策。
- 模型路由：外部 Profile 没有 adapter 时安全失败；密级 ceiling 和 `HIGHLY_RESTRICTED` 外发阻断由领域规则覆盖。
- 审计/证据：Compile create/execute、Wiki edit 和失败均审计；ModelInvocation、CompileStep、Outbox 与 SourceAnchor EvidenceCandidate 可回溯。
- 不可变性：Compile inputs、ModelInvocation、EntityVersion、WikiPageVersion、EvidenceCandidate 有数据库 trigger；AI 不能修改 protected sections。
- 无新依赖、无 Secret；不含客户/RCA 专用分支。

## 8. 风险与遗留项

- P0：0（本地范围）。
- P1：远程 CI/多架构供应链未运行；外部 LLM/embedding adapter 尚未配置，当前仅本地确定性 Provider；专门的 Compile Worker crash-window/归档 history 演练未单列执行。
- P2：业务准确率、引用准确率和性能阈值仍待经批准数据集/环境（OQ-METRIC-001）；Broker 外部投递、生产 HA/DR、RLS 纵深属于后续/部署门禁。

## 9. 需求追踪更新

- 已完成需求 ID：NXW-COMPILE-001/002、NXW-WIKI-001/002、NXW-SEMANTIC-003（Compile 边界）、NXW-SEMANTIC-004（候选边界）、NXW-CLAIM-002（候选链路）、NXW-CONFLICT-002（候选生成）、NXW-NFR-SEC-002（M5 路由边界）。
- 部分完成需求 ID：NXW-QUALITY-002、NXW-NFR-PERF-002、NXW-NFR-AVL-002；正式 Review/Evidence/Release/性能认证待后续。
- 未覆盖需求 ID：M6+ Review/Approval、M7 Evaluation/Release/Query、M8+ Connector/GridCrew、真实 OCR/外部模型与 RCA。

## 10. 停止声明

M5 已由用户正式验收。已停止在已验收 M5，未自行进入下一 Milestone。
