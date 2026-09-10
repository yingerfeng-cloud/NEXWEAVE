# NEXWEAVE M6 执行结果

## 1. 总体结论

- 阶段：本地技术验收通过，并于 2026-08-31 由用户正式验收。
- 是否满足进入下一阶段条件：否；M7 尚未下发，不进入 M7。
- Git 基线：未创建 commit 或 push；既有未提交工作区变更均被保留。

## 2. 实际完成范围

- 新增 Claim、Evidence、Conflict、ReviewPolicy、ReviewCase、ReviewTask、ReviewAction 的受治理闭环。
- 新增高风险固定三段审核、最终审核职责分离、有效 SourceAnchor 证据门禁与审核超时升级投影。
- 实现冲突显式聚类、保留双方和证据快照的可审计裁决，以及 Claim/Evidence、Conflict、Review Center 前端入口。

## 3. 关键变更文件

- `docs/architecture/adr/ADR-0025-m6-claim-evidence-conflict-review.md`：M6 Accepted 决策。
- `packages/domain/src/nexweave_domain/review.py`、`packages/contracts/src/nexweave_contracts/review.py`：纯领域规则及公共契约。
- `migrations/versions/0007_m6_claim_evidence_review.py`：追加式 M6 表、约束和不可变 trigger。
- `apps/api/src/nexweave_api/review_repository.py`、`review_routes.py`：审核、证据、冲突与质量 API。
- `workers/kernel/src/nexweave_worker_kernel/workflows.py`：`nexweave.human-review.v2`。
- `apps/web/src/ReviewCenter.tsx`、SDK、OpenAPI/JSON Schema、`scripts/verify_m6.py`：客户端与验证工具。

## 4. 领域对象、API、事件和 Workflow

- API：ReviewPolicy、Claim/Evidence 查询、ReviewCase/Task action、Conflict 检测/决策、ReviewQuality。
- Workflow：v1 不变；v2 等待经审计最终决定，超时产生 `APPROVAL_TIMEOUT_ESCALATED` 投影，并在完成前安全等待更新处理完成。
- 兼容性：仅新增 `0007_m6` 和 additive API/契约；未改写历史迁移。

## 5. 测试与验证

- `ruff check .`：通过；`mypy`：75 source files，无问题。
- `pytest -q`：109 passed。
- Web format/lint/typecheck 与 Vitest：13 tests passed；TypeScript SDK strict check 通过。
- `scripts/verify_m5.py`：以无外部模型调用的合成数据生成真实候选。
- `scripts/verify_m6.py`：高风险职责分离、Evidence gate、HumanReview v2、正式 Claim/Evidence、冲突决策审计全链通过。

## 6. 数据库与迁移

- 一次性真实迁移验证通过：`0001→0007→0005→0007`。
- M6 表与不可变 trigger 存在，M0—M4 sentinel 数据保留。

## 7. 安全、权限、审计与证据检查

- 服务端以 tenant、space、role 和 clearance 授权；高风险终审禁止创建人及先前审核人复用。
- 正式 Claim 与因果 Relation 审核要求有效锚点证据；Evidence、ConflictDecision、ReviewAction 为追加式事实。
- 无新依赖、无 Secret、无客户或 RCA 专用分支。

## 8. 风险与遗留项

- P1：远程 CI、外部模型适配、多架构供应链及专门 crash-window 演练未在本次未授权的本地收尾中执行。
- P2：质量、性能和可用性阈值仍依赖获批数据集与环境（OQ-METRIC-001）。

## 9. 需求追踪更新

- M6 对应 NXW-CLAIM、NXW-CONFLICT、NXW-REVIEW 与相关安全/审计需求已在需求追踪矩阵更新为正式验收完成。

## 10. 停止声明

M6 已由用户正式验收。已停止在 M6；未自行进入 M7。
