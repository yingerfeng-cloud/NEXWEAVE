# NEXWEAVE M0：终局架构冻结与工程骨架任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 产品版本：R1：可信知识闭环与联合试点版  
> 建议周期：2—3周  
> 执行对象：Codex  
> 上位基线：NEXWEAVE PRD V1.0、高保真原型 V1.0、M-1/M0后已批准架构与契约、完整开发任务总纲  
> 阶段原则：只执行本Milestone，完成后停止

---

## 1. 阶段定位

将 M-1 的候选基线正式冻结为可编码契约，并建立可启动、可测试、可持续演进的 Monorepo 工程骨架；本阶段仍不交付业务功能。

---

## 2. 前置条件

- M-1 验收通过，PRD、原型、架构基线、开放问题和追踪矩阵已归档。
- 关键 ADR 的决策人已明确，未决项能够在本阶段评审。

若前置条件不满足，必须在执行回报中列为P0阻塞，不得通过静默假设绕过。

---

## 3. 阶段目标

1. 冻结平台核心领域对象、状态机、版本语义、权限边界和错误码。
2. 冻结 API、事件、Temporal Workflow/Activity、幂等和状态投影契约。
3. 冻结数据库权威状态、Markdown 交换表示、Raw/Draft/Release 分层和 Domain Pack 扩展边界。
4. 建立前端、API、Workers、packages、infra、tests 的真实工程骨架和 CI。
5. 形成可运行的本地开发环境与最小健康检查，但不得实现业务页面和业务流程。

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


### 架构与ADR

- 评审并定稿 ADR-0001—ADR-0012；每项记录决策、替代方案、后果与迁移策略。
- 输出 C4 Context/Container/Component 图，明确模块化单体与独立 Worker 的物理边界。
- 冻结 Source、Schema、Page、Entity、Relation、Claim、Evidence、Conflict、Review、Evaluation、Release、DomainPack 等对象的 ID、租户、版本和审计字段。
- 明确 Temporal 为长任务权威状态，数据库保存业务投影；避免双状态源。
### 工程骨架

- 建立 Python/TypeScript Monorepo、统一 lint/typecheck/test/build 命令。
- 创建 apps/web、apps/api、workers、packages/domain、packages/contracts、packages/sdk、domain-packs、infra 和 tests。
- 建立配置分层、环境变量校验、密钥引用和开发/测试/生产环境隔离。
- 建立 Docker Compose：PostgreSQL、MinIO、Redis、Temporal、API、Web 最小服务；暂不要求 OpenSearch/Neo4j。
### 契约与数据

- 产出 OpenAPI 资源模型草案和 JSON Schema/Pydantic/TypeScript 契约单一来源策略。
- 冻结事件 envelope、correlation_id、causation_id、tenant_id、space_id、actor、occurred_at、schema_version。
- 建立 Alembic 基础迁移，只包含通用身份、空间、审计、outbox、系统配置和版本表骨架。
- 提供种子数据与脱敏 fixture 规范。
### 质量与治理

- 建立架构测试，阻断 domain/contracts 依赖 FastAPI、SQLAlchemy、Temporal 和厂商 SDK。
- 建立 CI：format、lint、typecheck、unit、contract、migration、frontend build、secret scan、dependency audit。
- 更新需求追踪矩阵，将每个 R1 需求映射到 M1—M9。

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

- 正式 ARCHITECTURE_BASELINE V1.0 与 ADR 决议。
- 可启动的 Monorepo、Docker Compose、CI 和健康检查。
- 冻结的领域、API、事件、Workflow、数据与错误码契约。
- 架构测试、契约测试骨架、种子数据和开发手册。

同时必须交付：

- 数据库迁移与回滚说明；
- OpenAPI/事件/SDK变更；
- 自动化测试与真实结果；
- ADR、需求追踪矩阵和CHANGELOG更新；
- 用户/管理员/开发者文档中与本阶段相关的增量。

---

## 10. 最低验收标准

- [ ] 一条命令可启动基础环境并通过 API/Web/Temporal/DB/MinIO 健康检查。
- [ ] 领域包与平台内核依赖方向有自动化门禁。
- [ ] 核心对象、状态、版本、API、事件和 Workflow 均无“待编码时再决定”的关键空白。
- [ ] 数据库迁移可正向执行并回滚；CI 在干净环境通过。
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
7. 不得实现真实知识空间、上传、编译、Wiki、审核、发布或问答功能。
8. 不得把原型静态数据当成后端功能完成。

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
# NEXWEAVE M0 执行结果

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
已停止在 M0，未自行进入下一 Milestone。
```

---

## 14. 交付判定

本阶段成功不以代码量或页面数量判断，而以“阶段目标形成真实、可测试、可审计、可迁移的纵向能力，并且不破坏平台通用性、证据链和Release语义”为准。
