# NEXWEAVE Documentation Index

## 阅读顺序

1. 根目录 `AGENTS.md`
2. 当前已执行待验收 Milestone：`development/tasks/04_NEXWEAVE_M2_Temporal可靠知识工作流内核任务书.md`
3. 根目录 `PRODUCT_BASELINE.md`、`ARCHITECTURE_BASELINE.md`、`OPEN_QUESTIONS.md`
4. `architecture/` 下的领域、数据、API、事件、Workflow、Pack 与 GridCrew 契约
5. `governance/` 下的命名、需求追踪、安全、质量和开发流程
6. `spikes/SPIKE_BACKLOG.md`
7. PRD、原型和 GridCrew 参考资料

## 权威关系

| 资料 | 版本/状态 | 用途 | 权威级别 |
|---|---|---|---|
| 用户当前明确指令 | 当前 | 范围、优先级和明确决策 | 最高 |
| 当前 Milestone 任务书 | M2 已执行、待用户验收 | 当前完成范围与验收边界 | 高 |
| `AGENTS.md` 与 Accepted ADR | 当前 | 工作规则与架构决策 | 高 |
| 根基线与需求追踪矩阵 | M2 增量待验收 | 冻结架构、契约与阶段追踪 | 高；M3 尚未下发 |
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

## 已发现的资料缺口

- `NEXWEAVE_原型预览.png` 缺失；
- `NEXWEAVE_Schema预览.png` 缺失；
- 未提供脱敏 Equipment RCA 报告、设备手册、IOE/LOE 或专家问题集；
- 原任务包 manifest 未覆盖嵌套 PRD/原型文件，仓库以 `governance/SOURCE_MANIFEST.md` 补充记录；
- Git 身份未配置，不得伪造提交身份。

原始交付目录 `NEXWEAVE_完整分阶段开发任务书_V1.0/` 未被覆盖或改写。
