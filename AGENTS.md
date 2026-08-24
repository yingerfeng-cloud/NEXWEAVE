# NEXWEAVE Codex 工作基线

## 权威资料优先级

执行任何任务前按以下顺序读取：

1. 用户当前明确指令；
2. 已批准的当前 Milestone 任务书；
3. 本文件；
4. 已接受的 ADR 与 `ARCHITECTURE_BASELINE.md`；
5. `PRODUCT_BASELINE.md` 与 `docs/governance/REQUIREMENTS_TRACEABILITY_MATRIX.md`；
6. PRD、原型和开发总纲；
7. GridCrew 参考资料及其他说明。

发生冲突时必须记录到 `OPEN_QUESTIONS.md` 并停止相关实现，不得选择最方便的解释。

## 当前阶段边界

- M-1 编码前治理基线已于 2026-08-23 由用户验收通过。
- 用户已于 2026-08-23 明确下发正式 M0，并于 2026-08-24 正式验收通过 M0；已披露的外部 CI、容器供应链与 RustFS SPK-004 风险继续作为 P1 跟踪。
- 当前没有已下发的活动 Milestone；只允许维护已验收 M0 基线和执行用户明确授权的收尾工作。
- M0 不包含 Source、Schema、Compile、Review、Release、Query、GridCrew 等业务功能实现。
- 未经用户单独明确下发，不得进入 M1 或后续 Milestone。
- 当前 Release 权威定义：R1 = M0—M9，R2 = M10—M12，R3 = M13—M15。

## 不可变产品与架构原则

- NEXWEAVE 是独立的可信知识平台，不是 GridCrew 子模块。
- Raw First、Schema Before Generation、Evidence Native、Human in the Loop。
- Draft 与 Release 分离；冲突不得静默覆盖；Release 不可原地修改。
- 平台核心不得包含客户、设备或 RCA 专用分支。
- Domain Pack 只能通过声明式契约扩展，不得依赖平台内部实现或执行任意代码。
- 模型调用必须经过 Model Gateway；外部资料和系统必须经过 Connector。
- 长任务使用可靠 Workflow；Workflow 定义不得直接执行网络、数据库、模型或文件 I/O。
- 权限、审计、Evidence、Release 和幂等不得被前端或集成层绕过。
- GridCrew 只能通过版本化 API、事件或 SDK 消费已发布知识，首期不得查询草稿或直接写正式知识。

## 变更规则

- 修改核心对象、状态、版本、API、事件、Workflow、SourceAnchor 或 Release 语义前，必须先新增或更新 ADR。
- `domain` 与 `contracts` 不得依赖 Web 框架、数据库、Temporal 或模型厂商 SDK。
- Workflow 只依赖确定性代码与契约；外部操作位于可重试、可观测、幂等的 Activity/Task。
- AI 生成代码必须配套测试、错误处理、审计和文档。
- 未确认需求必须进入 `OPEN_QUESTIONS.md`，不得静默假设。
- 不得修改历史数据库迁移；后续迁移必须可验证升级和回滚。
- 不得把静态原型、Mock、固定 JSON 或 LLM 文本冒充真实功能。

## 仓库与安全规则

- 不得覆盖、重置或删除用户已有修改和原始资料。
- 不得伪造 Git 用户身份、提交、测试、性能、专家确认或外部系统回执。
- 不得自动 push、创建远程仓库或进入下一 Milestone。
- 不得提交 API Key、密码、Cookie、真实敏感资料、内部地址或未脱敏日志。
- 新依赖必须记录用途、锁定版本、许可证、供应链风险和替代方案。

## 每阶段回报

每次执行结束必须报告：实际完成范围、变更文件、验证结果、迁移影响、安全与证据检查、需求追踪、风险/阻塞和停止声明。
