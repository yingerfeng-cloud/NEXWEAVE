# M9.5：Living Knowledge 可运行纵向首片

> 正式下发依据：2026-09-07 用户明确要求“先不考虑 M9 是否验收，先进行 M9.5 开发，先跑起来”。
> 当前范围：在现有平台增量实现并运行首片；不将 M9 验收作为开发前置，不进入 M10。

## 执行边界

用户最新指令替代 R2 规划中“必须先完成 M9 验收才能实施 M9.5”的顺序；M9 真实专家/批准阈值待办不删除、不伪造。ADR-0032 冻结本次实现。

交付真实 PostgreSQL 持久化、Temporal Workflow、S3 输入/输出、Chronos-2 实际权重推理、可替换数值 Provider、Schema 时序声明、SignalBinding、冻结 Context/Scenario、ForecastArtifact、PotentialEvent/风险叙述与现有 Wiki/Graph/Ask 页面入口。

现场 P-101 数据尚未提供。允许生成显著标记 SYNTHETIC / 非现场证据的 P-101 开发示例，用于跑通真实软件和模型；同时提供 CSV 上传/绑定通道。示例不是工业 Benchmark、现场 RCA 结论或已发布知识。没有正式 Release 时允许独立动态预测并展示“无已发布知识依据”，不得从草稿检索伪造正式引用。

## 最小范围

- 单个已建模实体、一个数值 Target，最多 8 个历史/未来数值协变量；规则采用声明式上阈值，数据/单位/角色/未来可获得性严格校验。
- SchemaVersion 是唯一语义权威；新增字段在缺席时不影响旧快照/签名；首片不改变 SourceAnchor/Evidence/Release。
- 原始 CSV 必须来自既有受控 SourceVersion，Connector 通过 ObjectStorage 读取，保留 hash；禁止任意 URL/SQL。
- 运行锁定 Source/Schema/Binding/模型/Scenario；实际执行为可靠 Workflow，推理与 I/O 在 Activity。失败可见，同请求键不能产生重复完成制品。
- UI 显示实际历史曲线、P10/P50/P90、假设场景比较、潜在越阈条件、来源/质量/任务状态；无 Chronos 中心，无自动控制/优化/GridCrew 执行。
- 阈值仅示例或用户配置；示例明确不可作现场报警。条件预测不等于因果推断，不输出故障概率。

## 验证与完成

单元/契约/隔离/负向/工作流边界、实际数据库迁移升级与隔离回滚、真实模型基线/场景两次运行、重复请求、错误输入、UI 渲染与原 R1 回归。提交执行报告、依赖锁版/许可、运行步骤、需求追踪和遗留项；不自动 commit/push。

完成判定为 M9.5 首片可运行，不代表真实工业试点通过或完整 R2 完成。
