# NEXWEAVE M4：Schema Studio与Domain Pack运行时任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 产品版本：R1：可信知识闭环与联合试点版  
> 建议周期：4—5周  
> 执行对象：Codex  
> 上位基线：NEXWEAVE PRD V1.0、高保真原型 V1.0、M-1/M0后已批准架构与契约、完整开发任务总纲  
> 阶段原则：只执行本Milestone，完成后停止

---

## 1. 阶段定位

建立“先定义知识结构再生成知识”的平台核心，使领域能力通过声明式 Pack 扩展而不侵蚀内核。

---

## 2. 前置条件

- M3 已提供统一 Source/Segment/Anchor。

若前置条件不满足，必须在执行回报中列为P0阻塞，不得通过静默假设绕过。

---

## 3. 阶段目标

1. 实现 EntityType、RelationType、PageTemplate、LintRule、EvaluationSuite 的配置与版本。
2. 实现 Schema 草稿、测试、发布、兼容检查和迁移预览。
3. 实现 Domain Pack manifest、签名、安装、升级、卸载、回滚和兼容校验。
4. 交付 equipment-rca-pack 的最小可安装样例，但不实现自动根因诊断。

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


### Schema服务

- 字段类型、必填、枚举、引用、唯一键、合并策略、关系方向、因果标识和证据要求。
- PageTemplate 定义 YAML 元数据、章节、自动生成区和人工保护区。
- SchemaVersion 不可覆盖；发布前执行兼容与影响分析。
### Schema Studio前端

- 实体/关系可视化设计、属性编辑、模板编辑、Lint规则和版本差异。
- 迁移预览展示受影响页面、实体、关系、Claim 与 Release。
### Domain Pack

- 定义安全的声明式 manifest，不允许任意代码执行。
- 实现 pack 校验、依赖解析、签名验证、安装记录和兼容矩阵。
- 创建 equipment-rca-pack：设备、部件、现象、故障模式、原因、验证、措施、案例等 Schema 与样例。
### 迁移与测试

- 实现向前兼容规则、破坏性变更阻断、测试空间安装、回滚和数据不丢失验证。

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
- 集成测试使用真实PostgreSQL、RustFS、Temporal等相关依赖；
- 前端测试覆盖关键组件、权限、错误、恢复和浏览器路由；
- 至少一条本阶段真实E2E链路，不得全部由Mock验收；
- 更新需求追踪矩阵、架构测试和安全测试；
- 新增依赖必须记录用途、版本、许可证和替代方案。

---

## 9. 阶段交付物

- Schema Service/Studio、Domain Pack SDK/CLI、Pack安装Workflow。
- equipment-rca-pack 最小样例与规范文档。

同时必须交付：

- 数据库迁移与回滚说明；
- OpenAPI/事件/SDK变更；
- 自动化测试与真实结果；
- ADR、需求追踪矩阵和CHANGELOG更新；
- 用户/管理员/开发者文档中与本阶段相关的增量。

---

## 10. 最低验收标准

- [ ] 可在不改平台代码的情况下安装一个新领域包并生成对应 Schema。
- [ ] 破坏性 Schema 变更会被识别并阻断直接发布。
- [ ] 卸载/回滚不删除既有知识，行为符合明确策略。
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
7. 不得允许 Domain Pack 直接执行任意 Python/JavaScript。
8. 不得为 RCA 单独新增核心表或硬编码字段。

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
# NEXWEAVE M4 执行结果

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
已停止在 M4，未自行进入下一 Milestone。
```

---

## 14. 交付判定

本阶段成功不以代码量或页面数量判断，而以“阶段目标形成真实、可测试、可审计、可迁移的纵向能力，并且不破坏平台通用性、证据链和Release语义”为准。
