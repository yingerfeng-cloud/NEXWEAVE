# NEXWEAVE M9 运行与联合试点手册

## 1. 当前可执行边界

M9 已正式下发。当前仓库可验证签名的 Equipment RCA Pack V1.0、跨 Pack 组合、安全问题集和既有 Source→Compile→Review→Evaluate→Release→Query 平台能力。ADR-0030 的 9 份/610 页 NTSB 公开资料已完成仅文本准入，4 份代表性报告已完成真实 Pack→Source→Compile 技术试点；GridCrew 联合试点延期。本手册不把候选编译、本地 Provider 或单边 API 调用计作专家验收结果。

## 2. Pack 本地验证

```bash
export PYTHONPATH="apps/api/src:packages/domain/src:packages/contracts/src:packages/application/src:workers/kernel/src"
.venv/bin/python scripts/verify_m9_pack.py
.venv/bin/pytest -q packages/domain/tests/test_m9_equipment_rca_pack.py
```

预期结果：manifest/Ed25519/checksum 有效；`core-pack → equipment-rca-pack` 与 `core-pack → maintenance-pack` 确定性组合；公共 Equipment 只出现一次；所有因果 Relation 要求 Evidence；标准问题集覆盖六类行为；合成 fixture 明确 `pilotEvidence=false`；平台运行时代码没有 RCA stable key 或 KKS 分支。

## 3. 真实资料准入

每一份公开事故调查、RCA、IOE、LOE 或设备手册进入 Source 前，资料所有者/准入责任人必须批准并记录：

- 来源、授权依据、所有者和允许用途；
- 原始密级、脱敏人、脱敏方法与复核人；
- 是否允许发送到外部模型；若不允许，固定内网/本地 ModelProfile；
- 保留期限、删除/撤回流程、Raw checksum 和 SourceVersion；
- 页码/段落/表格等可验证 SourceAnchor 预期；
- 对应试点设备/案例范围，不得以标题或设备编码充当稳定实体身份。

未通过准入不得导入，也不得复制到测试 fixture。公开批次及逐页排除见 `PUBLIC_SOURCE_CATALOG.md`、`PUBLIC_SOURCE_ADMISSION_REPORT.md` 和 accession manifest；必须排除第三方照片、插图、地图、厂商摘录和附件，默认不得发往外部模型。仓库中的 `synthetic-rca-case.json` 只测试格式，不是脱敏后的真实资料。

NTSB 原 PDF 带可无密码阅读的加密标志，平台仍按安全基线拒绝直接解析。正确处理是保留原 PDF Raw/SourceVersion 与失败审计，在内存中生成仅文本派生件、排除 manifest 指定页，再创建独立 SourceVersion；不得关闭加密 PDF 拒绝策略或把派生件覆盖 Raw。

## 4. 真实纵向闭环

1. 以受控 Connector 或上传会话创建 Raw 和不可变 SourceVersion，完成扫描/解析并核验 checksum 与 Anchor。
2. 登记 Pack 公钥和 `equipment-rca-pack@1.0.0`，解析精确 `core-pack` 依赖；安装只生成 DRAFT SchemaVersion。
3. 由独立 Publisher 验证并发布 SchemaVersion，记录 composition checksum 与 PackVersion/checksum 输入。
4. 固定 SourceVersion、SchemaVersion、PromptVersion、ModelProfile 创建 CompileJob；模型只产生候选。
5. 专家审核实体合并、因果 Relation、支持/反向 Evidence、验证方法、Conflict 和页面保护区；高风险内容执行职责分离。
6. 把 Pack 标准问题集实例化为 M7 EvaluationSuite，并补齐每题预期 Claim/术语；运行逐题 EvaluationRun。
7. 仅当来源可追溯率和 Schema 合规率均为 100%、无阻断 Lint/Conflict、评测通过且独立 Publisher 批准时发布不可变 RCA Release。
8. 以固定 Release 验证相似案例、因果路径、支持/反向证据、验证建议和证据不足拒答；不得输出自动处置。
9. 回滚演练只移动 ReleasePointer；失败或修正产生新候选/版本，不修改历史 Release。

当前技术试点已完成步骤 1—4，并强制停在候选态。步骤 5—9 必须由真实专家/发布人参与后另行执行；运行事实见 `docs/development/evidence/m9-public-pilot/TECHNICAL_PILOT_RUN_2026-09-02.md`。

## 5. GridCrew 联合准入（延期）

用户已通过 ADR-0030 明确 GridCrew 暂不开发，联合 Demo、联合故障演练和验收全部延期。GridCrew 缺失不再是 M9 P0，但不得描述为完成或通过。

未来重新启动时，仍必须同时具备：GridCrew 可运行版本、服务身份、tenant mapping、Skill Version/EmployeeRelease 固定资产、NEXWEAVE `space_id/release_id/policy_version` 绑定、允许操作列表、双方错误码、correlation ID、审计查询、重试策略和签名事件/Webhook fixture。直接调用 NEXWEAVE API 或 Mock GridCrew 仍不计联合验收。

## 6. 指标记录

指标定义和空白记录见 `M9_PILOT_ACCEPTANCE_TEMPLATE.md`。阈值栏只能填写经产品/RCA 专家批准的值。每个比例必须保留分子、分母、排除项和失败样本，不能只报告百分比。

## 7. 故障演练

- 模型超时：Workflow 重试/失败可见，不产生正式知识；
- 解析失败：保留 Raw/SourceVersion 与失败单元，不能伪造 Anchor；
- 审核退回：产生追加式 ReviewAction，新版本修正；
- 发布失败：ReleaseCandidate 保持历史，不切换指针；
- 回滚：只推进指针版本，不改变 Release checksum；
- GridCrew 重试：按 ADR-0030 延期；未来仅在真实对端就绪并由用户单独下发后执行。

## 8. 停止边界

M9 未完成专家评审、批准指标、正式 Evaluation/Release/Query 前不得宣布阶段通过或进入 M10。公开资料准入和 4 份 Source→Compile 技术导入已经完成，但不能替代专家签署。GridCrew 已延期，不再是 M9 P0，也不得被补造为完成；不得自行补造指标、专家签名、对端回执或外部模型结果。
