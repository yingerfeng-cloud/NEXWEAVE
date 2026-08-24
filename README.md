# NEXWEAVE｜织界

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台。

当前仓库已完成并正式验收 **M0 终局架构冻结与工程骨架**：架构/公共契约、最小 API、Web、Temporal Worker、基础迁移、Compose、CI 和测试骨架已经交付，本地七服务启动、真实 E2E 与迁移回滚均已通过。知识业务功能尚未开始。

## 当前状态

- Release 基线：R1 = M0—M9；
- 最近验收 Milestone：用户于 2026-08-24 正式验收通过 M0；同日完成远程基线、干净 GitHub CI、容器供应链门禁与 RustFS SPK-004 收尾；
- 业务代码：未开始；当前代码仅验证工程底座；
- M0 技术基线：Python 3.12/FastAPI、React/TypeScript、Temporal、PostgreSQL/pgvector、RustFS/S3、Redis；
- 下一阶段：M1 未开始，必须等待用户单独明确下发。

## M0 本地启动

```bash
make dev-up
make verify
```

详见 [`docs/development/M0_RUNBOOK.md`](docs/development/M0_RUNBOOK.md)。

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
- 本仓库当前不声称已完成登录、资料、编译、Wiki、审核、发布、问答、GridCrew 集成或 RCA 诊断。
