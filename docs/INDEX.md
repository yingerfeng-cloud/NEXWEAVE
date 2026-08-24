# NEXWEAVE Documentation Index

## 阅读顺序

1. 根目录 `AGENTS.md`
2. 最近验收 Milestone：`development/tasks/02_NEXWEAVE_M0_终局架构冻结与工程骨架任务书.md`
3. 根目录 `PRODUCT_BASELINE.md`、`ARCHITECTURE_BASELINE.md`、`OPEN_QUESTIONS.md`
4. `architecture/` 下的领域、数据、API、事件、Workflow、Pack 与 GridCrew 契约
5. `governance/` 下的命名、需求追踪、安全、质量和开发流程
6. `spikes/SPIKE_BACKLOG.md`
7. PRD、原型和 GridCrew 参考资料

## 权威关系

| 资料 | 版本/状态 | 用途 | 权威级别 |
|---|---|---|---|
| 用户当前明确指令 | 当前 | 范围、优先级和明确决策 | 最高 |
| 最近验收 Milestone 任务书 | M0 已验收 | 已完成范围与验收证据 | 高 |
| `AGENTS.md` 与 Accepted ADR | 当前 | 工作规则与架构决策 | 高 |
| 根基线与需求追踪矩阵 | M0 已验收 | 冻结架构、契约与阶段追踪 | 高，等待下一 Milestone 下发 |
| 完整开发总纲 | V1.0 | Release、Milestone、全局门禁 | 高 |
| PRD | V1.0 | 产品功能与初始 NFR | 上位产品输入 |
| 高保真原型 | V1.0 | 信息架构和交互目标 | 视觉/交互参考，非功能实现 |
| GridCrew 资料 | V2.2/M-1C | 共享原则与集成兼容参考 | 参考，不覆盖 NEXWEAVE |

## 目录

- `product/nexweave/`：NEXWEAVE 产品资料的只读治理副本；
- `development/tasks/`：完整分阶段任务书的原样副本；
- `reference/gridcrew/`：选定 GridCrew 产品、架构、ADR 和任务参考；
- `reference/domain/rca/`：待提供的脱敏 RCA 领域资料；
- `architecture/`：M0 冻结架构、公共契约与 Accepted ADR；
- `governance/`：命名、追踪、安全、质量和研发流程；
- `spikes/`：仍需在对应能力前执行的技术验证计划；
- `development/M0_RUNBOOK.md`：可复现 M0 启停、验证和诊断。

## 已发现的资料缺口

- `NEXWEAVE_原型预览.png` 缺失；
- `NEXWEAVE_Schema预览.png` 缺失；
- 未提供脱敏 Equipment RCA 报告、设备手册、IOE/LOE 或专家问题集；
- 原任务包 manifest 未覆盖嵌套 PRD/原型文件，仓库以 `governance/SOURCE_MANIFEST.md` 补充记录；
- Git 身份未配置，不得伪造提交身份。

原始交付目录 `NEXWEAVE_完整分阶段开发任务书_V1.0/` 未被覆盖或改写。
