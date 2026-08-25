# NEXWEAVE｜织界

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台。

当前仓库的 **M2 Temporal 可靠工作流内核已于 2026-08-25 正式验收并停止**：M1 平台、身份、空间、审计与对象基础已验收；M2 新增七类 Temporal Workflow 的通用可靠执行骨架、任务投影、真实任务中心、控制 API、故障恢复与官方时间跳跃验证。M2 Activity 仅形成内核 Stub 事实，不代表 Source、Compile、Review、Release 等后续知识业务已经实现。

## 当前状态

- Release 基线：R1 = M0—M9；
- 最近验收 Milestone：M2 于 2026-08-25 正式验收；
- 已实现业务边界：身份与权限、KnowledgeSpace、治理配置、托管对象，以及 M2 通用 WorkflowTask/Step/Event 查询投影；
- 技术基线：Python 3.12/FastAPI、React/TypeScript、Temporal、PostgreSQL/pgvector、RustFS/S3、Redis；
- 下一阶段：M3 未下发，必须等待用户单独明确指令。

## M2 本地启动与验证

```bash
make dev-up
make verify
make verify-m2
```

详见 [`docs/development/M2_RUNBOOK.md`](docs/development/M2_RUNBOOK.md)。

## 阅读顺序

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/INDEX.md`](docs/INDEX.md)
3. [`PRODUCT_BASELINE.md`](PRODUCT_BASELINE.md)
4. [`ARCHITECTURE_BASELINE.md`](ARCHITECTURE_BASELINE.md)
5. [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)
6. 最近验收的 Milestone 任务书；新 Milestone 下发后以新任务书替换

## 禁止误解

- `NEXWEAVE_完整分阶段开发任务书_V1.0/` 是用户原始交付包，保留原文；
- `docs/product/` 与 `docs/development/tasks/` 是仓库内受治理副本；
- 高保真 HTML 是交互参考，不是生产前端；
- 本仓库不把七类 M2 Kernel Stub 冒充资料解析、真实编译、审核业务、发布、问答、GridCrew 集成或 RCA 诊断。
