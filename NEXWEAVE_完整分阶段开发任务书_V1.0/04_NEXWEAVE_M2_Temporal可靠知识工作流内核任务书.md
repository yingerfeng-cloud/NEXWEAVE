# NEXWEAVE M2：Temporal可靠知识工作流内核任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 产品版本：R1：可信知识闭环与联合试点版  
> 建议周期：3周  
> 执行对象：Codex  
> 上位基线：NEXWEAVE PRD V1.0、高保真原型 V1.0、M-1/M0后已批准架构与契约、完整开发任务总纲  
> 阶段原则：只执行本Milestone，完成后停止

---

## 1. 阶段定位

建立资料解析、知识编译、人工审核、质量评估、发布、领域包安装和反馈回流的统一可靠执行机制。

---

## 2. 前置条件

- M1 的身份、空间、审计、Outbox 和基础存储可用。

若前置条件不满足，必须在执行回报中列为P0阻塞，不得通过静默假设绕过。

---

## 3. 阶段目标

1. 实现 Temporal Namespace、Task Queue、Worker 部署和健康监控。
2. 实现七类基础 Workflow 的状态、Signal/Update、取消、超时、重试、补偿和投影。
3. 形成 Workflow 确定性、Activity 幂等和故障恢复测试体系。

---

## 4. 不可变约束

1. Raw First：原始资料及其版本、哈希、来源和密级是事实基线，LLM 不得覆盖原文。
2. Schema Before Generation：未绑定有效 SchemaVersion 的知识编译不得进入正式流水线。
3. Evidence Native：正式 Claim 与因果 Relation 必须绑定可定位 Evidence。
4. Human in the Loop：高风险知识、冲突处理和 Release 必须经过人工审核与批准。
5. Draft / Release Separation：草稿、审核中对象和正式 Release 必须逻辑隔离，业务应用默认只读 Release。
6. Conflict Instead of Overwrite：新资料与既有知识不一致时生成 Conflict，不静默覆盖。
7. Version Reproducibility：回答、审核、评估和发布均可还原 Source、Schema、Prompt、Model 与 Release 版本。
8. Platform / Domain Decoupling：平台核心不得写死 RCA、核电、泵、轴承等领域概念。
9. Gateway First：模型、解析器、搜索、对象存储和外部系统均通过 Gateway/Provider/Connector 接口接入。
10. Reliable Workflow：长任务、人工审核、发布和跨系统回流必须由 Temporal 等可靠工作流承载。
11. Audit by Default：关键读写、模型调用、审核、导出、发布、回滚与权限变更必须审计。
12. GridCrew Boundary：NEXWEAVE 独立部署，GridCrew 通过版本化 API、事件与 SDK 消费知识。

---

## 5. 详细建设任务


### Workflow实现

- SourceIngestionWorkflow：上传完成后的扫描、解析准备和状态更新。
- KnowledgeCompileWorkflow：定义可扩展步骤图，先以 Stub Activity 跑通。
- HumanReviewWorkflow：分派、领取、补充资料、驳回、批准和超时升级。
- QualityEvaluationWorkflow、KnowledgeReleaseWorkflow、DomainPackInstallWorkflow、GridCrewFeedbackIngestionWorkflow。
### 可靠性

- 定义 Workflow ID、Run ID、幂等键、业务主键映射与重复请求行为。
- Activity 分类设置超时、指数重试、不可重试错误、心跳和取消。
- 数据库投影只读展示 Temporal 状态；建立对账和修复任务。
- 实现 Worker 宕机、网络失败、Activity 重放、重复消息、取消和补偿演练。
### 任务中心

- 实现统一任务列表、详情、步骤、日志、重试、暂停/继续/取消入口。
- 所有动作进行权限、状态和幂等校验。
### 测试

- Workflow replay 测试、时间跳跃测试、幂等测试、故障注入测试和状态对账测试。

---

## 6. 前后端与交互要求

1. 以高保真原型的信息架构和交互目标为基线，但不得照搬静态数据或仅做页面模拟；
2. 所有列表、详情、状态、权限、错误、空状态、加载、重试和审计均由真实API驱动；
3. 页面必须支持深链接、刷新恢复和浏览器返回，不得依赖仅内存状态；
4. 长任务必须展示Temporal业务状态、步骤、错误和可执行动作；
5. 权限和密级在服务端执行，前端只负责提示与交互；
6. UI保持NEXWEAVE深色知识操作系统设计语言，并满足可访问性、响应式和国产浏览器适配基线。

---

## 7. 数据、API、事件和版本要求

1. 新增或修改对象必须更新domain、contracts、OpenAPI、事件、数据库迁移和SDK；
2. 所有写接口定义权限、幂等键、乐观锁、审计和错误码；
3. 所有异步接口返回业务对象ID与Workflow ID，不以临时线程ID作为业务标识；
4. 迁移必须提供升级和可验证回滚方案，不得修改历史迁移；
5. 所有对象明确tenant_id、space_id、状态、版本、创建者和更新时间；
6. 任何Release、Evidence和SourceAnchor语义变化必须有ADR和兼容策略。

---

## 8. 测试与质量要求

- 单元测试覆盖本阶段领域规则、状态机、权限和错误分支；
- 契约测试覆盖OpenAPI、事件、SDK和Provider/Connector边界；
- 集成测试使用真实PostgreSQL、MinIO、Temporal等相关依赖；
- 前端测试覆盖关键组件、权限、错误、恢复和浏览器路由；
- 至少一条本阶段真实E2E链路，不得全部由Mock验收；
- 更新需求追踪矩阵、架构测试和安全测试；
- 新增依赖必须记录用途、版本、许可证和替代方案。

---

## 9. 阶段交付物

- Temporal 基础设施、Workflow/Activity SDK、任务投影与任务中心。
- 可靠性与故障演练报告。

同时必须交付：

- 数据库迁移与回滚说明；
- OpenAPI/事件/SDK变更；
- 自动化测试与真实结果；
- ADR、需求追踪矩阵和CHANGELOG更新；
- 用户/管理员/开发者文档中与本阶段相关的增量。

---

## 10. 最低验收标准

- [ ] 所有长任务均可查询、取消、恢复且不会产生重复业务对象。
- [ ] Workflow 代码不直接调用网络、数据库、文件或模型。
- [ ] Worker 重启后任务继续；重复请求返回同一业务结果或明确冲突。
- [ ] 全局CI门禁通过；
- [ ] 无新增P0安全、架构、证据或版本问题；
- [ ] 用户已有修改未被覆盖；
- [ ] 执行回报与真实代码、测试结果一致。

---

## 11. 禁止事项

1. 不得绕过权限、审计、Evidence、Release、Model Gateway 或 Connector 直接访问底层能力。
2. 不得在平台核心中加入客户专用、设备专用或 RCA 专用条件分支。
3. 不得修改已发布 Release 内容；修正必须形成新版本或补丁版本。
4. 不得伪造测试结果、性能数据、专家确认、Git 身份、提交记录或外部系统回执。
5. 不得覆盖用户已有未提交修改、重置仓库或自动 push。
6. 不得自行进入下一 Milestone；完成后必须停止并按指定格式回报。
7. 不得用普通后台线程、Celery 临时任务或数据库轮询替代已冻结的可靠 Workflow。
8. 不得将页面状态作为任务权威状态。

---

## 12. 建议执行步骤

1. 读取AGENTS.md、总纲、当前任务书、已批准ADR和上阶段执行回报；
2. 盘点仓库、测试、迁移和未提交修改；
3. 更新需求追踪与本阶段实施计划；
4. 先实现领域和契约，再实现基础设施适配和API；
5. 实现前端真实闭环；
6. 补齐审计、权限、证据、错误与可观测性；
7. 执行单元、契约、集成、E2E和故障/安全测试；
8. 做架构债务和兼容性检查；
9. 更新文档与CHANGELOG；
10. 按回报格式输出并停止。

---

## 13. Codex最终回报格式

```markdown
# NEXWEAVE M2 执行结果

## 1. 总体结论
- 阶段：通过 / 有条件通过 / 不通过
- 是否满足进入下一阶段条件：是 / 否
- Git 基线：提交哈希 / 未提交及原因

## 2. 实际完成范围
- 按任务书章节逐项说明，不得只写概括结论。

## 3. 新增或修改文件
- 文件路径：用途、核心变更、对应需求 ID。

## 4. 领域对象、API、事件和 Workflow 变更
- 新增：
- 修改：
- 兼容性影响：
- ADR：

## 5. 测试与验证
- 命令：
- 结果：
- 未执行项及原因：

## 6. 数据库与迁移
- 迁移文件：
- 回滚验证：
- 数据兼容性：

## 7. 安全、权限、审计与证据检查
- 结论与证据：

## 8. 风险与遗留项
- P0：
- P1：
- P2：

## 9. 需求追踪更新
- 已完成需求 ID：
- 部分完成需求 ID：
- 未覆盖需求 ID：

## 10. 停止声明
已停止在 M2，未自行进入下一 Milestone。
```

---

## 14. 交付判定

本阶段成功不以代码量或页面数量判断，而以“阶段目标形成真实、可测试、可审计、可迁移的纵向能力，并且不破坏平台通用性、证据链和Release语义”为准。
