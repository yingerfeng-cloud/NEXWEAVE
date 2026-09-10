# 阶段 D：验收与可信边界执行报告

日期：2026-09-10。依据用户阶段 D 指令与“验收与可信边界收口”选择、11F 和 ADR-0036，完成本地技术验证；不是用户正式验收、M9 专家批准或工业效果验收。停止在 D / M9.5，不进入 M10。

## 实际完成

- 新 Query 只使用当前有效引用支持的冻结 Claim 正文，不将未支持的召回文本或未发布冲突明细混入回答。Citation 检查同 Release Claim/Evidence、Anchor、来源密级、归档与失效；整条多来源 Claim 按全部冻结来源的当前最高密级控制。
- 历史 QueryAnswer 在读取/重放时重新鉴权、过滤引用并重新构造受支持陈述；增加 `read_checked_at/read_filtered` 响应说明，不修改历史存储。读取者还须满足创建会话的密级要求。重放键同时核对发布、问题、策略与检索参数；差异返回 409。
- Graph 从发布快照读取节点和关系，校验起点/终点、同发布 Evidence 及当前来源有效性。4000 实体/2000 关系候选预算溢出明确拒绝，输出 500 边上限明确标记；最短路径不受展示截断误导。错误或无时区日期返回 422。
- 前端切换发布/空间/起点时清除旧图谱，忽略过期异步响应，显示截断提示。
- 真实验收发现并修复两项问题：实体快照不存在 attributes 导致 Graph 500；主页面重复添加路径斜杠导致“查看原文定位”不跳转。后者补主页面→SourceCenter 集成回归。

## 变更文件

核心实现：`apps/api/src/nexweave_api/release_repository.py`、`release_graph.py`、`release_routes.py`；契约 `packages/contracts/src/nexweave_contracts/release.py`、runtime 版本、导出 JSON Schema/OpenAPI 与 API 版本描述；前端 `App.tsx`、`M7Knowledge.tsx`。

验证：`apps/api/tests/test_stage_d_reads.py`、`test_app.py`、`apps/web/src/M7Knowledge.test.tsx`、`AppNavigation.test.tsx`、`scripts/verify_stage_d.py`、`verify_stage_d_graph.py`。

治理：11F、ADR-0036、本报告/运行手册/证据、AGENTS、架构/产品基线、RTM、状态与索引。精确增量文件和哈希见随附 `阶段D_运行证据.json`，按阶段开始时的工作区快照比较，未把此前未提交工作算成本阶段实现。

## 验证结果

- 162 Python 测试通过，5 个 integration 项未在该命令运行；33 前端测试通过；Python/前端 lint、类型检查、前端构建通过。无新增依赖。
- 真实 HTTP：正常 Query 完成、同键重放、5 类参数/发布冲突拒绝；已失效来源的旧答案变为当前读取 REFUSED，引用/正文依据不再返回；Graph 正常成员、2 项非成员拒绝、2 项日期拒绝通过。C 知识回接及旧预测哈希检查通过。
- 真实 PostgreSQL 会话临时表：6 项 Graph 验证通过，2 项多来源 Claim 密级验证通过；全部临时 DDL/数据回滚，业务表只读。
- 实际浏览器：CSV 1440 行预览及映射预检通过；变更后保存禁用，错误单位拒绝。已有预测对照显示末端分位数与非因果说明；固定发布返回明确标为合成的相关材料。原文入口最终显示 VALID、block 与字符定位命中。发布图谱正常显示并在换版本后清空，非成员拒绝。
- API/Web 已部署；HTTP 报告确认预测 worker 在线且版本 `0.9.5-d1`，排队/运行均为 0。本阶段未重复运行 Chronos-2。

## 迁移、安全与证据检查

无新迁移；11 个历史迁移文件与 D 开始快照一致，无升级/回滚需求。未变更已有 ForecastArtifact、Release、Evidence 或合成失效来源；未改变正式发布指针。HTTP 验证只增加测试 Query 与审计记录；浏览器预检未保存新绑定。Secret pattern scan 通过，证据文件不包含凭据。没有提交或推送，也没有覆盖原始资料与已有修改。

需求追踪：NXW-LK-D-001—005 覆盖 Query/历史读取、Graph、浏览器与兼容边界；B/C 原“未新增完整浏览器点击验收”由本阶段列明的关键路径验证补充，不能解释为全站所有组合已验收。

## 风险与停止边界

- 工业数据、Chronos-2 相对基线 Benchmark、区间校准、专家阈值/适用性与 M9 真实评审 P0 仍开放；合成结果不能证明 Chronos-2 已适合现场运行。
- 本次不是全系统安全审计或并发/生产负载认证。新 Query 同键首次并发竞争的完整故障恢复演练未覆盖；读时权限并发变更的事务一致性、所有角色/来源状态组合和生产 OIDC 仍需专项验证。
- Graph 当前有界整图读取，规模超过预算需未来演进；现有页面仍需手工输入起点实体标识。浏览器正向发布只含节点；正向关系与其他负向组合通过真实数据库隔离测试验证，未伪造浏览器有边结果。
- 保留原有签名时序 Pack、现场 Connector、生产服务化/HA 等待办；不以本次收口预先认定 Chronos-2 为最终工业 Provider。Forecast 仍是派生结果，条件预测仍不等于因果推断。
- 上次浏览器流程曾因额度耗尽被自动审批中断；本次用户续接后恢复并完成上述检查。停止在阶段 D，不进入 M10。
