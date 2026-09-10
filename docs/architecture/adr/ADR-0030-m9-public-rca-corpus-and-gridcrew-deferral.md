# ADR-0030: M9 公开 RCA 候选语料与 GridCrew 联合试点延期

- Status: Accepted
- Date: 2026-09-01
- Approval basis: 用户明确要求从网络获取一批材料，并决定 GridCrew 暂不开发、联合试点延期且通过 ADR 留痕
- Decision owners: 用户、产品、架构、安全、领域治理负责人
- Supersedes: ADR-0029 第 6、7 条中“GridCrew 缺失构成 M9 P0/总体不通过”的部分；其余证据边界继续有效
- Related: ADR-0001, ADR-0011, ADR-0027, ADR-0029, OQ-RCA-001, OQ-M9-DATA-001, OQ-M9-EXPERT-001, OQ-M9-GRID-001

## Context

M9 尚无客户提供的 RCA、IOE、LOE 或设备手册。用户授权从网络寻找公开材料，同时明确 GridCrew 暂不开发、联合试点延期。公开可访问不等于可无限复制、训练或向外部模型传输；政府报告也可能嵌入第三方照片、图形或附件。因此需要把来源真实性、版权边界、Raw checksum、模型使用范围和试点结论分开治理。

已从 NTSB 官方站点取得 9 份已完成事故调查报告，共 610 页，覆盖柴油发电机、紧固件、轴承/润滑、冷却系统、航空涡轮盘、管道腐蚀/检测和铁路热轴承。NTSB 网站政策说明其工作人员履职形成的网页、报告和建议内容通常不受版权保护并进入公共领域，但其中标识为第三方的文字、照片、插图或其他材料不随之获得再利用授权。

## Decision

1. 建立 `M9-PUBLIC-RCA-CANDIDATE-2026-09-01` 公开候选语料批次。原始 PDF 保存在被 Git 忽略的 `.nexweave-data/m9-public-sources/`，仓库只保存可审计的来源目录和 accession manifest；不得把网络 URL、标题或网页摘要冒充已经导入的 SourceVersion。
2. 每份候选资料必须记录官方 URL、获取日期、字节数、页数、SHA-256、来源机构、许可依据、第三方内容风险、允许用途和当前准入状态。重新下载后 checksum 变化必须形成新 accession 记录，不得覆盖历史事实。
3. 首轮试点只允许使用 NTSB 自有正文、表格和由其明确创作的内容。标注 Courtesy/Source 的第三方照片、插图、地图、厂商手册片段、docket 附件和商标/徽章默认排除；需要使用时必须单独核权。
4. 候选语料当前密级为 PUBLIC，但在完成逐份准入、解析质量和隐私复核前，不得形成正式 RCA Release。默认只允许本地、无网络的解析与确定性 ModelProfile；发送到外部模型仍需单独批准并记录 ModelProfile、用途与保留策略。
5. 该批材料可用于 NEXWEAVE 独立的“公开资料 Equipment RCA 技术试点”，验证 Source→Compile→Review→Evaluate→Release→Query、Evidence 定位和拒答。它不等价于客户现场 RCA/IOE/LOE，不得据此声称客户业务适配、行业专家认可、实时诊断或自动处置能力。
6. GridCrew 暂不开发。GridCrew 固定 Release 调用、Skill/EmployeeRelease 绑定、身份/租户映射、反馈回流、重试和联合故障演练全部延期到用户未来单独下发的联合里程碑，并在届时通过新的双边 ADR/契约评审重新准入。
7. GridCrew 缺失不再构成 M9 验收 P0，也不属于当前 M9/R1 的通过条件；它保持 `DEFERRED` 且不得被描述为完成、通过或已联调。ADR-0029 的 Mock 禁止、固定 Release、服务身份和双边审计边界继续有效。
8. M9 的剩余 P0 是具备签署权限的领域专家、获批准的指标阈值和真实评审记录。公开语料的“存在性缺口”已解除，但其逐份准入、真实纵向导入和专家评测仍未完成，所以本决策本身不构成 M9 验收通过，也不授权进入 M10。

## Compatibility and migration

- 不修改平台核心对象、API、事件、Workflow、SourceAnchor、Evidence 或 Release 语义，不需要数据库迁移。
- 不删除 ADR-0001/0011 的长期 GridCrew 独立部署与固定 Release 约束；只改变当前 M9 的范围和阻塞判定。
- 公开语料导入时继续使用 M3—M7 已验收的 Source、Compile、Review、Evaluation 和 Release 契约，不建立第二套数据或评测权威。

## Validation

- 下载文件必须为可解析 PDF，页数与清单一致，SHA-256 可复算。
- manifest 必须是有效 JSON，9 个 source ID、URL、文件名和 checksum 均唯一。
- 导入前执行逐份许可/第三方内容、隐私、解析质量和外部模型准入检查。
- 文档和追踪矩阵必须把 GridCrew 标为延期而非 P0/完成，把专家评审保留为 P0。
- M9 仍停止在本阶段；没有用户明确验收和单独下发，不得进入 M10。
