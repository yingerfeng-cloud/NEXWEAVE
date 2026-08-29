# NEXWEAVE Documentation Index

## 阅读顺序

1. 根目录 `AGENTS.md`
2. 当前已正式下发并进入实施的 Milestone：`development/tasks/05_NEXWEAVE_M3_资料中心、版本管理与文档解析任务书.md`；同时读取最近正式验收的 M2 任务书与执行报告
3. 根目录 `PRODUCT_BASELINE.md`、`ARCHITECTURE_BASELINE.md`、`OPEN_QUESTIONS.md`
4. `architecture/` 下的领域、数据、API、事件、Workflow、Pack 与 GridCrew 契约
5. `governance/` 下的命名、需求追踪、安全、质量和开发流程
6. `spikes/SPIKE_BACKLOG.md`
7. PRD、原型和 GridCrew 参考资料

## 权威关系

| 资料 | 版本/状态 | 用途 | 权威级别 |
|---|---|---|---|
| 用户当前明确指令 | 当前 | 范围、优先级和明确决策 | 最高 |
| 当前 Milestone 任务书 | M3 已正式下发，执行前校准完成 | 当前实施范围与验收边界 | 高；正式实施进行中，仍不得提前声称已完成 |
| `AGENTS.md` 与 Accepted ADR | 当前 | 工作规则与架构决策 | 高 |
| 根基线与需求追踪矩阵 | M2 增量已验收；M3 治理状态已更新 | 冻结架构、契约与阶段追踪 | 高；M3 功能尚未实现 |
| 完整开发总纲 | V1.0 | Release、Milestone、全局门禁 | 高 |
| PRD | V1.0 | 产品功能与初始 NFR | 上位产品输入 |
| 高保真原型 | V1.0 | 信息架构和交互目标 | 视觉/交互参考，非功能实现 |
| GridCrew 资料 | V2.2/M-1C | 共享原则与集成兼容参考 | 参考，不覆盖 NEXWEAVE |

## 目录

- `product/nexweave/`：NEXWEAVE 产品资料的只读治理副本；
- `development/tasks/`：完整分阶段任务书的原样副本；
- `reference/gridcrew/`：选定 GridCrew 产品、架构、ADR 和任务参考；
- `reference/domain/rca/`：待提供的脱敏 RCA 领域资料；
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
- `development/tasks/05_NEXWEAVE_M3_资料中心、版本管理与文档解析任务书.md`：已按 M0—M2 实况校准的 M3 直接执行边界；当前不代表功能实现。
- `architecture/adr/ADR-0021-m3-source-parse-version-and-anchor-semantics.md`：M3 Source/Parse 版本、v1/v2 Workflow、部分失败/OCR_REQUIRED 与 Anchor 语义。

## 已发现的资料缺口

- `NEXWEAVE_原型预览.png` 缺失；
- `NEXWEAVE_Schema预览.png` 缺失；
- 未提供脱敏 Equipment RCA 报告、设备手册、IOE/LOE 或专家问题集；
- 原任务包 manifest 未覆盖嵌套 PRD/原型文件，仓库以 `governance/SOURCE_MANIFEST.md` 补充记录；
- 仓库已使用用户既有 Git 身份完成获授权的历史提交；后续仍不得伪造或擅自变更提交身份。

原始交付目录 `NEXWEAVE_完整分阶段开发任务书_V1.0/` 未被覆盖或改写。
