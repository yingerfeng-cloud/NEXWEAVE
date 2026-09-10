# ADR-0029: M9 Equipment RCA Pack 与联合试点边界

- Status: Accepted（第 6、7 条中 GridCrew 作为 M9 P0/验收条件的部分已被 ADR-0030 替代）
- Date: 2026-09-01
- Approval basis: 用户正式下发 M9；M8 已正式验收；既有 OQ-GRID-001 与 OQ-RCA-001 仍约束外部联调和真实资料
- Decision owners: 产品、架构、安全、领域治理负责人
- Related: OQ-GOV-015, OQ-GRID-001, OQ-RCA-001, OQ-METRIC-001, ADR-0001, ADR-0009, ADR-0011, ADR-0022, ADR-0026, ADR-0027

> 2026-09-01 后续决策：用户通过 ADR-0030 将 GridCrew 暂不开发及联合试点延期，并批准建立公开 RCA 候选语料。以下第 6、7 条保留为当时决策历史；当前阻塞与验收判定以 ADR-0030 为准。

## Context

M9 需要以 Equipment RCA Domain Pack 验证从资料、Schema、编译、审核、质量到不可变 Release 和可信查询的纵向价值，同时不得把设备或 RCA 语义写入平台核心。当前 M8 的 Connector、Obsidian 和 Wiki 图谱已验收，但 GridCrew 对端仍处规划期；仓库也未取得经授权的脱敏 RCA/IOE/LOE/手册、专家名单或批准的量化门槛。任务书明确禁止通过静默假设、Mock 回执或伪造专家确认绕过这些前置条件。

## Decision

1. `equipment-rca-pack` V1.0 只以签名、JSON-only、不可执行的声明式 Pack 交付。设备、部件、现象、报警、故障模式、直接原因、根本原因、机理、验证、排除、措施、案例、专家规则、KKS/设备编码、术语、模板、Prompt、Lint、UI 元数据和标准问题集全部位于 Pack；平台核心不得出现 RCA 专用状态、字段、分支或自动诊断逻辑。
2. Pack 依赖公共 `core-pack` 的 Equipment 类型，并以受控 `maintenance-pack` fixture 验证跨 Pack 复用。重复 key、层级/端点冲突、歧义 mapping 或签名/checksum 不一致继续由 M4 通用组合规则阻断；Pack 安装只生成 DRAFT SchemaVersion，发布仍需独立授权。
3. M9 的回答契约定位为辅助知识分析：只允许返回固定 Release 中的候选原因、支持/反向证据、验证建议、已知冲突与证据不足。不得输出实时诊断、故障概率、自动处置指令或最终工程判断。
4. 未经授权的真实 RCA 资料不得加入仓库或发往外部模型。仓库内可提交明确标记为 `SYNTHETIC` 的技术 fixture，用于验证格式、组合、门禁和拒答；这些结果不得计入真实试点、专家接受率、引用准确率、覆盖率或人工修改比例。
5. 真实试点必须保存资料准入清单、脱敏/授权证明、SourceVersion/checksum、固定 Schema/Prompt/Model/Release、逐题结果、专家评审身份与时间、指标分子分母和失败样本。阈值只能由产品/RCA 专家批准，不能由实现者自行设定。
6. GridCrew 联合能力继续遵守 ADR-0001/0011 的独立部署、服务身份、固定 Release、双边审计和反馈仅入草稿边界。由于对端契约、身份/租户映射和可联调环境尚不存在，本阶段不得实现或声称真实 GridCrew 联动；只保留已冻结的 NEXWEAVE 公共 Release API/SDK/Event 能力和对端准入检查表。
7. M9 可以完成本地技术验收，但在真实资料、专家和 GridCrew 前置未满足前，阶段总体结论只能是“不通过/被 P0 阻塞”，不能形成 R1 联合试点验收或宣称可进入 M10。

## Compatibility and migration

- 本决策不新增平台核心对象，不修改 Release、Evidence、SourceAnchor、Workflow 或数据库语义，因此不需要 M9 数据库迁移。
- Pack V1.0 使用既有 M4 `v1alpha1` manifest、签名、组合与安装契约；标准问题集可映射到既有 M7 `EvaluationSuite`，不引入第二套评测权威。
- 历史 SchemaVersion、PackVersion 和 Release 不受 Pack 文件新增或后续升级影响。

## Validation

- Pack：JSON Schema、Ed25519、内容 checksum、命名空间所有权、确定性组合、跨 Pack 复用、不可执行内容、卸载/禁用不影响平台测试。
- 标准问题集：至少覆盖可回答、不可回答、冲突、反事实、多证据和证据不足；辅助定位、安全免责声明和反向证据要求可机器检查。
- 架构：扫描平台核心，确认没有 `equipment-rca`、KKS、设备类型或自动处置专用分支。
- 真实试点与 GridCrew：在外部前置就绪后另行执行，结果必须来自真实系统和批准数据，不接受 Mock 代替。
