# M9 Equipment RCA 公开资料技术试点验收记录模板

> ADR-0030 已将 GridCrew 联合试点延期。下列 GridCrew 字段仅保留为未来扩展占位，不参与当前 M9/R1 判定。

> 状态：EMPTY / NOT EVIDENCE。由授权产品负责人、RCA 专家与双方集成负责人在真实试点中填写；当前仓库不包含任何专家确认或真实指标。

## 0. 已完成技术预填（非专家验收）

| 项目 | 技术事实 |
|---|---|
| 技术试点空间 | `01a060fa-1c1f-7280-a63e-0d4512284ceb` |
| Pack Installation | `01a060fa-1c2d-7a17-be4a-023b4a9cffaa` / `ACTIVE` |
| SchemaVersion | `01a060fa-1c73-7a05-907c-fed9722d0aa0` / `PUBLISHED` |
| composition checksum | `sha256:5ccbf47f553d31d97857fe23c1a22f654ea49ca76e3ace372466756be2b6891e` |
| 公开资料 | 4 份代表性 NTSB 报告，Raw 保留、文本派生解析成功 |
| 候选结果 | 368 ClaimCandidate / 377 EvidenceCandidate / 9 RelationCandidate |
| 正式对象 | Claim 0 / ReviewCase 0 / Release 0 |
| 专家/阈值 | 未批准；本节不得用于填写最终签署 |

完整运行 ID 和审计边界见 `docs/development/evidence/m9-public-pilot/TECHNICAL_PILOT_RUN_2026-09-02.md`。

## 1. 试点身份

| 项目 | 值 |
|---|---|
| 试点 ID | 待填写 |
| 设备/案例范围 | 待批准 |
| 数据所有者与授权记录 | 待提供 |
| 脱敏复核人/日期 | 待提供 |
| NEXWEAVE Release ID/version/checksum | 待运行 |
| SchemaVersion/composition checksum | 待运行 |
| PackVersion/checksum | 待运行 |
| PromptVersion/ModelProfile | 待运行 |
| GridCrew Skill Version/EmployeeRelease | DEFERRED（不参与本次验收） |

## 2. 专家与职责分离

| 角色 | 姓名/身份 | 范围 | 签署时间 |
|---|---|---|---|
| 知识工程师 | 待提供 | 建设与初审 | 待填写 |
| RCA 领域专家 | 待提供 | 专业复核 | 待填写 |
| 独立发布人 | 待提供 | Release 批准 | 待填写 |
| 质量/审计 | 待提供 | 指标与证据抽查 | 待填写 |
| GridCrew 集成负责人 | DEFERRED | 未来联合链路 | 不参与本次验收 |

## 3. 指标定义与结果

| 指标 | 计算口径 | 批准阈值 | 分子 | 分母 | 结果 | 证据引用 |
|---|---|---:|---:|---:|---:|---|
| 来源可追溯率 | 发布 Claim/因果 Relation 中具备 accepted Evidence + VALID Anchor 的数量 / 全部发布 Claim/因果 Relation | 100%（任务书固定） | 待运行 | 待运行 | 待运行 | 待填写 |
| Schema 合规率 | 符合固定 SchemaVersion 的发布对象 / 全部发布对象 | 100%（任务书固定） | 待运行 | 待运行 | 待运行 | 待填写 |
| 引用准确率 | 专家判定引用直接支持回答陈述的 Citation / 抽查 Citation | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |
| 问题覆盖率 | 达到批准通过规则的标准问题 / 批准纳入的问题 | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |
| 专家接受率 | 无需实质修改即接受的回答 / 专家评审回答 | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |
| 人工修改比例 | 需要实质知识修改的候选对象 / 专家评审候选对象 | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |
| 术语歧义处置率 | 已显式映射/拒绝/保留歧义的术语 / 发现歧义术语 | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |
| 跨 Pack 查询正确率 | 专家确认正确的跨 Pack 查询 / 纳入的跨 Pack 查询 | 待专家批准 | 待运行 | 待运行 | 待运行 | 待填写 |

## 4. 标准问题逐题记录

| case key | 类型 | 结果 | Answer ID | Citation IDs | 专家结论 | 修改/失败原因 |
|---|---|---|---|---|---|---|
| similar-case-with-basis | ANSWERABLE | 待运行 |  |  |  |  |
| causal-path | MULTI_SOURCE | 待运行 |  |  |  |  |
| verification-methods | ANSWERABLE | 待运行 |  |  |  |  |
| conflicting-sources | CONFLICT | 待运行 |  |  |  |  |
| counterfactual | COUNTERFACTUAL | 待运行 |  |  |  |  |
| unanswerable-live-diagnosis | UNANSWERABLE | 待运行 |  |  |  |  |
| insufficient-evidence | INSUFFICIENT_EVIDENCE | 待运行 |  |  |  |  |

## 5. 故障演练记录

| 场景 | 预期 | Workflow/Release/Task 证据 | 结果 |
|---|---|---|---|
| 模型超时 | 可恢复或诚实失败；不发布 | 待运行 | 待运行 |
| 解析失败 | Raw 保留；失败单元可见 | 待运行 | 待运行 |
| 审核退回 | 追加动作；新版本修正 | 待运行 | 待运行 |
| 发布失败 | 不切指针；候选历史保留 | 待运行 | 待运行 |
| Release 回滚 | 只移动指针 | 待运行 | 待运行 |
| GridCrew 重试 | ADR-0030 延期 | DEFERRED | 不参与本次验收 |

## 6. 最终签署

- 系统定位已确认为辅助知识分析、不替代最终工程判断：待专家签署
- 是否满足批准阈值：待判定
- P0/P1/P2：待填写
- 是否接受 M9/R1 公开资料技术试点：待授权人明确决定
- GridCrew 联合试点：DEFERRED，不得在本记录中填写为通过
