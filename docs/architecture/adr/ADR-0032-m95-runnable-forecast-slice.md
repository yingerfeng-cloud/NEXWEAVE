# ADR-0032：M9.5 可运行预测首片实现契约

- Status: Accepted for M9.5 implementation
- Date: 2026-09-07
- Approval basis: 用户明确要求先进行 M9.5 开发并跑起来，M9 验收不再作为开发前置；在该授权内冻结最小技术实现，不代表专家签署工业指标。
- Supersedes: ADR-0031 中 M9.5 开发依赖 R1 先验收的提案顺序；其他长期提案继续保留。

## 冻结决策

1. 新增独立 ForecastRepository，以组合复用平台授权/事务审计，不延长 R1 仓储继承链。
2. Schema 时序声明为 `signalDefinitions` 与 `forecastProfiles`；缺席/空值不进入旧规范化快照；有时序字段的快照带明确扩展版本。组合、类型引用、角色/单位和配置验证在领域/契约执行，不把任意 UI JSON 作为语义权威。
3. SignalBinding 固定实体/SchemaVersion/SourceVersion、CSV 列、角色与单位；新增修订另建绑定。ForecastContext 保存明确数值窗口、质量检查、时间网格、Scenario、来源 checksum；不可变绑定/Context/Artifact/Assessment 保存在新增表。
4. Observation 作为有 SourceVersion/行/列/时间定位的冻结窗口值对象存于受控制品；不建立无限制实时采集库。只读 TimeSeriesConnector 从已准入 SourceVersion 的 ObjectStorage 读取 CSV，限字节/行列/网格/数值有限性，严格不补造缺测。
5. ForecastRun 独立状态 QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED；Temporal 独立预测队列，输入仅持久化 ID。成功制品不可变；重复执行提交幂等，失败任务可新运行且保留旧事实。
6. TimeSeriesModelProvider 由数值 Model Gateway 统一限资源/输入/策略/审计；Chronos2Provider 在推理 Worker lazy import，固定官方 checkpoint 与依赖。基线仅用于声明能力范围内的对照，不静默替代 Chronos。
7. 首片单 Target、数值协变量、严格规则网格、最多 8192 历史步/120 未来步、P10/P50/P90。未来路径由用户显式指定，保存 USER_ASSUMPTION，不叫实际未来；模型能力不支持时拒绝。
8. PotentialEvent 仅表示分位曲线触及规则条件；event_probability 为 null。Hypothesis/Risk Narrative 使用有类型的预测引用和可选的固定 Release 引用，无正式知识时明确不足，不以草稿/示例文字制造 Evidence。
9. 首片允许 SYNTHETIC 开发窗口与示例规则，并在 UI/Artifact/报告保留该身份；既有知识平台无 P-101/泵/温度专用分支，实例和声明在示例/Pack 文件中。
10. Wiki/Graph/Ask 增加显式“运行与预测”视图，复用稳定实体与 URL 上下文；旧固定 Release Query/Citation 行为不变。
11. 新增 additive 0010_m95；现有迁移不变，隔离库验证降级。新写入授权复用现有 governance/manage、compile/create 等权限并明确操作审计；所有动态读取重新检查 tenant/space 与输入密级。

## 限制与验证

仅本地技术首片；现场测点/阈值/工业 Benchmark 尚未确认，不阻塞技术开发但阻止工业效果声明。独立模型服务保持内网执行，演示知识不自动 Release；GridCrew/OptiForge 不实施。

具体接口/字段以新增 contracts/OpenAPI 和测试为准；新增依赖锁版、许可证与替代方案进入 DEPENDENCY_BASELINE。执行后报告实际运行与限制，不用 Mock 验收模型。
