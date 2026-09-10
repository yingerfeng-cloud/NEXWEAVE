# NEXWEAVE Documentation Index

## 阅读顺序

1. 根目录 `AGENTS.md`
2. 当前 Milestone：M8 已于 2026-08-31 正式验收；M9 与其 M9-FE 补充整治已于 2026-09-01 正式下发。M9-FE 已完成本地技术验收并停止；M9 公开资料准入和 4 份 Source→Compile 技术试点已完成，专家/阈值/评审与 Release 仍为 P0；GridCrew 联合试点延期
3. 根目录 `PRODUCT_BASELINE.md`、`ARCHITECTURE_BASELINE.md`、`OPEN_QUESTIONS.md`
4. `architecture/` 下的领域、数据、API、事件、Workflow、Pack 与 GridCrew 契约
5. `governance/` 下的命名、需求追踪、安全、质量和开发流程
6. `spikes/SPIKE_BACKLOG.md`
7. PRD、原型和 GridCrew 参考资料

## 权威关系

| 资料 | 版本/状态 | 用途 | 权威级别 |
|---|---|---|---|
| 用户当前明确指令 | 当前 | 范围、优先级和明确决策 | 最高 |
| 当前 Milestone 任务书 | M9 已正式下发 | 当前实施范围与验收边界 | 高；不得自行进入 M10 |
| M9-FE 任务书与前端设计系统基线 | 已正式下发；本地技术验收完成 | M9/R1 前端视觉、结构、响应式与验收边界 | 高；不改变业务语义、不构成 M10 |
| `AGENTS.md` 与 Accepted ADR | 当前 | 工作规则与架构决策 | 高 |
| 根基线与需求追踪矩阵 | M1—M8 已正式验收，M9 执行中 | 冻结架构、契约与阶段追踪 | 高；P0 不得静默关闭 |
| 完整开发总纲 | V1.0 | Release、Milestone、全局门禁 | 高 |
| PRD | V1.0 | 产品功能与初始 NFR | 上位产品输入 |
| 高保真原型 | V1.0 | 信息架构和交互目标 | 视觉/交互参考，非功能实现 |
| GridCrew 资料 | V2.2/M-1C | 共享原则与集成兼容参考 | 参考，不覆盖 NEXWEAVE |

## 目录

- `product/nexweave/`：NEXWEAVE 产品资料的只读治理副本；
- `development/tasks/`：完整分阶段任务书的原样副本；
- `reference/gridcrew/`：选定 GridCrew 产品、架构、ADR 和任务参考；
- `reference/domain/rca/`：公开 RCA 候选资料目录、checksum/许可准入 manifest 与未来客户资料边界；
- `architecture/`：M0 冻结架构、M1/M2 增量公共契约与 Accepted ADR；
- `governance/`：命名、追踪、安全、质量和研发流程；
- `spikes/`：仍需在对应能力前执行的技术验证计划；
- `development/M1_IMPLEMENTATION_PLAN.md`：M1 实施边界与验收映射；
- `development/M1_RUNBOOK.md`：可复现 M1 启停、使用、生产配置、验证和诊断；
- `development/reports/NEXWEAVE_M1_执行报告.md`：M1 实际变更与验证证据。
- `development/M2_IMPLEMENTATION_PLAN.md`：M2 实施边界与验收映射；
- `development/M2_RUNBOOK.md`：M2 启停、任务控制、投影对账、故障恢复与验证；
- `development/reports/NEXWEAVE_M2_可靠性与故障演练报告.md`：M2 真实可靠性演练证据；
- `development/reports/NEXWEAVE_M2_执行报告.md`：M2 实际变更、条件项与停止声明。
- `development/tasks/05_NEXWEAVE_M3_资料中心、版本管理与文档解析任务书.md`：已按 M0—M2 实况校准并于 2026-08-29 正式验收；代码、本地门禁与远程供应链门禁已完成。
- `development/reports/NEXWEAVE_M3_执行与验收报告.md`：M3 实际范围、真实验证、远程供应链证据、遗留项与停止声明。
- `architecture/adr/ADR-0021-m3-source-parse-version-and-anchor-semantics.md`：M3 Source/Parse 版本、v1/v2 Workflow、部分失败/OCR_REQUIRED 与 Anchor 语义。
- `architecture/adr/ADR-0022-m4-semantic-model-schema-authority-pack-composition.md`：M4 语义模型、SchemaVersion 单一权威与 Pack 确定性组合决策。
- `architecture/adr/ADR-0023-m4-pack-implementation-contract.md`：M4 stable key、canonical Pack、签名/撤销、迁移 DSL 与声明式 UI 实现契约。
- `architecture/SEMANTIC_MODEL_BASELINE.md`：稳定 key、类型/属性/层级/关系、术语/映射、版本和安全边界。
- `governance/SEMANTIC_MODEL_IMPACT_MATRIX.md`：M5—M15 强制/定向影响与逐阶段校准触发器。
- `development/tasks/06_NEXWEAVE_M4_Schema Studio与Domain Pack运行时任务书.md`：M4 已于 2026-08-30 正式验收，停止等待 M5 单独下发。
- `development/reports/NEXWEAVE_M4_语义模型治理校准报告.md`：实施前历史校准结论与当时停止声明。
- `development/reports/NEXWEAVE_M4_执行与验收报告.md`：M4 实际范围、真实迁移/E2E/安全证据、独立审查修复、风险与停止声明。
- `development/M4_RUNBOOK.md`：M4 Schema/Pack 操作、验证、诊断、安全和停止边界。
- `architecture/adr/ADR-0024-m5-compile-wiki-model-contract.md`：M5 固定编译输入、Model Gateway、稳定身份、Wiki 保护区和 v1/v2 兼容决策。
- `development/tasks/07_NEXWEAVE_M5_LLM知识编译核心与Wiki工作台任务书.md`：M5 已正式下发、完成本地技术验收并正式验收通过。
- `development/M5_RUNBOOK.md`：M5 编译/Wiki 操作、验证、模型供应商边界、诊断与停止边界。
- `development/reports/NEXWEAVE_M5_执行与验收报告.md`：M5 实际范围、真实迁移/E2E/安全证据、风险与停止声明。
- `architecture/adr/ADR-0025-m6-claim-evidence-conflict-review.md`：M6 Claim/Evidence、冲突和专家审核的实现级决策。
- `development/M6_RUNBOOK.md`、`development/reports/NEXWEAVE_M6_执行与验收报告.md`：M6 已正式验收的本地证据、运行与停止边界。
- `architecture/adr/ADR-0026-m7-quality-release-query-projection.md`：M7 质量事实、不可变发布、投影、回滚与单 Release 查询决策。
- `development/M7_RUNBOOK.md`、`development/reports/NEXWEAVE_M7_执行与验收报告.md`：M7 已正式验收的隔离真实 E2E、运行方式、风险与停止边界。
- `architecture/adr/ADR-0027-m8-connector-obsidian-boundary.md`、`architecture/adr/ADR-0028-m8-wiki-bidirectional-link-graph.md`、`development/M8_RUNBOOK.md` 与 M8 报告：已正式验收的 M8 边界与证据。
- `architecture/adr/ADR-0029-m9-equipment-rca-pack-and-pilot-boundary.md`、`architecture/adr/ADR-0030-m9-public-rca-corpus-and-gridcrew-deferral.md`、`reference/domain/rca/PUBLIC_SOURCE_CATALOG.md`、`development/M9_RUNBOOK.md`、`development/evidence/m9-public-pilot/TECHNICAL_PILOT_RUN_2026-09-02.md` 与 M9 报告：M9 Pack/公开资料技术链、专家 P0 和 GridCrew 延期边界。
- `development/tasks/11A_NEXWEAVE_M9-FE_前端设计系统与高保真原型对齐重构任务书.md`、`design/NEXWEAVE_FRONTEND_DESIGN_SYSTEM_BASELINE.md`、`design/NEXWEAVE_M9-FE_VISUAL_DEVIATIONS.md` 与 `development/reports/NEXWEAVE_M9-FE_前端重构执行与验收报告.md`：M9-FE 设计系统、全路由迁移、视觉偏离、浏览器证据、独立审查和停止边界。
- `design/FRONTEND_UI_AUDIT.md`、`design/FRONTEND_DESIGN_SYSTEM.md` 与 `development/reports/FRONTEND_REFACTOR_REPORT.md`：2026-09-07 桌面优先 UX/UI System Refactor 的当前审查、规范、PASS/PARTIAL 验收、四档桌面截图与遗留风险。

## 已发现的资料缺口

- `NEXWEAVE_原型预览.png` 缺失；
- `NEXWEAVE_Schema预览.png` 缺失；
- 未提供客户侧脱敏 Equipment RCA 报告、设备手册、IOE/LOE 或专家问题集；已有 NTSB 公开候选报告尚待逐份准入和专家评审；
- 原任务包 manifest 未覆盖嵌套 PRD/原型文件，仓库以 `governance/SOURCE_MANIFEST.md` 补充记录；
- 仓库已使用用户既有 Git 身份完成获授权的历史提交；后续仍不得伪造或擅自变更提交身份。

原始交付目录 `NEXWEAVE_完整分阶段开发任务书_V1.0/` 未被覆盖或改写。

## 阶段 A：R1 + M9.5 稳定基础

- [11C 任务书](development/tasks/11C_NEXWEAVE_阶段A_稳定基础.md)
- [ADR-0033](architecture/adr/ADR-0033-stage-a-runtime-recovery.md)
- [运行手册](development/STAGE_A_RUNBOOK.md)
- [执行报告](development/reports/NEXWEAVE_阶段A_稳定基础执行报告.md)
- [运行证据](development/reports/阶段A_运行证据.json)

## 阶段 B：自主绑定与条件场景

- [11D 任务书](development/tasks/11D_NEXWEAVE_阶段B_自主运行闭环.md)
- [ADR-0034](architecture/adr/ADR-0034-stage-b-self-service-binding.md)
- [运行手册](development/STAGE_B_RUNBOOK.md)
- [执行报告](development/reports/NEXWEAVE_阶段B_自主运行执行报告.md)
- [运行证据](development/reports/阶段B_运行证据.json)

## 阶段 C：固定发布知识回接

- [11E 任务书](development/tasks/11E_NEXWEAVE_阶段C_已发布知识回接.md)
- [ADR-0035](architecture/adr/ADR-0035-stage-c-released-knowledge-context.md)
- [运行手册](development/STAGE_C_RUNBOOK.md)
- [执行报告](development/reports/NEXWEAVE_阶段C_知识回接执行报告.md)
- [运行证据](development/reports/阶段C_运行证据.json)

## 阶段 D：验收与可信边界收口

- [11F 任务书](development/tasks/11F_NEXWEAVE_阶段D_验收与可信边界收口.md)
- [ADR-0036](architecture/adr/ADR-0036-stage-d-trusted-read-boundary.md)
- [运行手册](development/STAGE_D_RUNBOOK.md)
- [执行报告](development/reports/NEXWEAVE_阶段D_验收与可信边界执行报告.md)
- [运行证据](development/reports/阶段D_运行证据.json)
