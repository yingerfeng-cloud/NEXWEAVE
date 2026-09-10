# ADR-0031: Living Knowledge 增量架构与时序模型边界（提案）

- Status: **Proposed — 未批准实施**
- Date: 2026-09-07
- Request basis: 用户要求先完成 R1 Architecture Consolidation Review 与 R2 重规划，不立即大规模修改代码
- Decision owners: 待产品/架构/设备专家/数据与安全负责人确认
- Related: ADR-0010、0014、0016、0022—0030；NXW-LK-001—009（提案）；OQ-LK-001—008
- Full design: [R1 Consolidation / R2 Living Knowledge Review](../R1_CONSOLIDATION_R2_LIVING_KNOWLEDGE_REVIEW.md)

## Context

现有 R1 已有单一 SchemaVersion、声明式 Pack、Raw/Claim/Evidence/Review/Release、可靠 Workflow、图谱/问答和真实前端，但模型实际实现以本地编译/哈希 embedding 为主，Connector 以文件字节为单位。当前无工业观察/预测领域契约，M9 的真实专家/阈值/发布试点仍有 P0。

用户期望将静态可信知识演进为能描述运行状态、变化与未来条件预测的 Living Knowledge；要求 Chronos-2 只是首发 Provider，平台不成为工业采集、控制或数学优化系统。

## Alternatives

1. 把时序与 Chronos 响应塞进 Claim/Entity 属性/LLM 文本：成本看似低，但混淆观测/推断/预测、缺时间版本与模型可替换性，否决。
2. 重建 Ontology/Release，换全新图数据库/微服务/时序平台：无测量证据支持，破坏 R1 权威与投入，否决。
3. 在现有平台增量建立 Operational Knowledge、Forecasting、Dynamic Interpretation 模块，复用治理和存储边界：**建议采用**。

## Proposed decisions

1. 定级为中等架构调整、增量实施；保留 R1 核心与历史语义。新应用服务以端口组合实现，不继续延长仓储继承链。
2. Ontology 继续是 SchemaVersion 的语义视图。时序声明经新版本契约/确定性组合发布，旧 Pack checksum 与旧 schema 读取保持兼容；不新增 OntologyVersion。
3. 新增 SignalDefinition/Binding、Observation、OperationalContext、ForecastContext/Run/Artifact、PotentialEvent、Hypothesis，认识来源与治理资格分轴表达。
4. TimeSeriesConnector 只读授权窗口、保留稳定 Raw SourceVersion/回执；外部 Historian 留作大规模运行数据权威。NEXWEAVE 只存受控重放窗口/元数据和派生制品，不变为采集平台。
5. TimeSeriesModelProvider 是 Model Gateway 管治下的数值预测能力端口。Chronos2Provider、基线、TimesFM/私有/工业模型只在 adapter/Worker 层出现；不支持能力必须显式拒绝，不能静默丢弃协变量。
6. Context Builder 按批准 profile/binding 自动解析 Target/Past/Future/Context，锁时间网格、available_at、plan issued_at、质量、修订、单位、Schema/Pack/Release 和预处理；不让 LLM 猜测测点。
7. ForecastArtifact 永远是模型派生制品。PotentialEvent/Hypothesis/风险叙述不自动成为 Evidence、Claim 或 Release；时序 Evidence 的直接接入另行冻结 locator ADR。
8. Scenario 以未来路径为条件，不是因果干预。不以 P90 越阈计算故障概率，不用三个边际分位数推导窗口/联合事件概率。
9. 旧 Query 保持单一固定 Release；新增显式 DynamicAssessment 固定一个 Release + 观察/预测/场景引用，分层返回 typed citations。Graph 动态覆盖层不成为事实权威。
10. UI 增量落在 Wiki/Schema/Graph/Ask/集成/RCA 空间；无 Chronos 中心。业务动作和优化继续由 GridCrew/OptiForge 在未来单独授权的接口中承担。
11. 建议 M9.5 真实 P-101 历史回放/条件预测桥接，benchmark 决定 Go/限定 Go/更换模型/No-Go；原 M10—M12 治理、检索评测与生产责任保留。

## Compatibility and migration proposal

仅采用新增迁移/版本化资源与事件。历史 SourceAnchor、Evidence、Release、Schema 快照/签名、Workflow 类型不重写；旧客户端不接收不能解析的新字段。动态能力可独立关闭，回退保留制品/审计与 R1 sentinel。高频数组入对象存储，关系库保留 scope/version/provenance/状态与索引。

## Acceptance before implementation

- 产品明确 M9.5 定位、范围与下发；R1 未验收时不能用新计划覆盖旧 P0。
- 数据与专家确认 P-101 身份、授权窗口、测点字典、计划历史、规程/阈值与 benchmark。
- 将本 ADR 的设计方向细化为正式对象状态机、能力/错误/API/event/SDK/迁移与新旧兼容契约。
- 验证 R1 Graph 起点/节点权限、历史节点版本与截断风险；未清楚前不扩大相关能力。
- 首个真实 Provider + 简单基线/失败路径 + 现有 UI 三入口 Real E2E；无数据/模型时不以合成 fixture 验收。
- 后续至少一个真实替代 Provider 通过同契约验证；权重/依赖许可按固定版本逐项登记。

本 ADR 没有批准人签署，不使上述提案变成已接受基线。本轮未创建业务代码、迁移、API 或模型运行。
