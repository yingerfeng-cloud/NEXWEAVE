# ADR-0025: M6 Claim、Evidence、冲突与人工审核实现契约

- Status: Accepted
- Approval basis: 用户于 2026-08-30 明确下发“请执行M6”；本 ADR 是编码前治理校准
- Date: 2026-08-30
- Decision owners: 平台管理员设全局护栏；空间管理员配置审核策略；知识工程/领域专家/批准人执行个案审核
- Related: ADR-0004, ADR-0008, ADR-0013—0016, ADR-0021, ADR-0022, ADR-0024

## Decision

- M5 `ClaimCandidate`、`EvidenceCandidate` 与 `CandidateRelation` 保留为不可发布候选。M6 新增追加式正式 `Claim` 与 `Evidence` 记录；正式 Claim 保存 Subject-Predicate-Object、scope、有效期、可信等级及创建时的可复现 provenance。Evidence 固定 SourceAnchor、excerpt hash、来源权威等级、支持/反对/上下文方向、审核状态和可选截图引用。原始 Source、SourceVersion 与 Anchor 从不被审核修改。
- 任何正式 Claim 或具有因果语义的 Relation 在进入批准状态前均须至少一个 `VALID` SourceAnchor 的已接受 Evidence；反向证据不会删除支持证据。Anchor 失效会使相关 Evidence 标为失效并重新打开未完成审核，绝不静默移除历史事实。
- 冲突以可聚类 `ConflictCase` 表示，保留每一侧的 Claim/候选和 Evidence 引用。唯一允许的裁决为 `RETAIN_BOTH`、`CONDITIONAL`、`MERGE`、`UNRESOLVED`、`EXPIRED` 与 `REOPEN`，每次裁决为追加式含理由、比较快照与操作者的记录；阻断冲突在未决时不得绕过 Release。
- 审核策略为按空间、风险等级版本化的声明。空间管理员配置受平台管理员护栏约束；不在代码中固化业务 SLA、来源权威或批量范围。默认流程是知识工程师初审、领域专家复核、负责人批准；策略可省略低风险的负责人批准并允许有上限的低风险批处理。高风险一律三阶段，创建人不能担任最终批准人，且批准人不能代替前序审核人。
- 每一个审核对象有稳定 ReviewCase、Temporal `HumanReview v2` Workflow、阶段化 ReviewTask 和追加式 ReviewAction。领取、修改、接受、驳回、补充资料、转交、超时升级和恢复均通过 API/Workflow 信号留下审计；对象修改使用版本快照/diff 和理由，不覆写历史审核意见。
- M2 `HumanReview v1` 保持历史 Kernel Stub；M6 真实业务使用 `nexweave.human-review.v2`。Workflow 只协调确定性状态和等待；数据库、通知和投影由幂等 Activity 承担。

## Consequences

M6 只把经人工审核的 Draft Claim/Evidence 转化为受治理的批准对象，未实现 Release、正式 Query 或图投影。改变审核阶段、职责分离、Evidence/Conflict 状态或将审批结果纳入 Release 时，必须以新 ADR 和追加迁移兼容。
