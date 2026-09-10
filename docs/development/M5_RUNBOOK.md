# NEXWEAVE M5 Runbook

> 范围：受治理 Compile、候选知识和版本化 Wiki 草稿。M5 不包含 M6 Review、正式 Evidence 决策、Release 或 Query。

## 1. 启动与健康检查

```bash
make dev-up
curl --fail http://127.0.0.1:8000/api/v1/health/ready
curl --fail http://127.0.0.1:8000/api/v1/version
```

API version 应报告 `M5`/`0.6.0-m5`；数据库 head 应为 `0006_m5`。Web 代理在 API 容器重建后若短暂保留旧地址，可重启 Web，或诊断时直接使用 API 的 8000 端口。

## 2. 编译前置条件

1. SourceVersion 状态为 `PARSED` 或 `PARTIAL`，并固定 active ParseJob/checksum；
2. SchemaVersion 必须为 `PUBLISHED`，CompileJob 固定其 composition checksum；
3. PromptVersion 与 ModelProfile 必须可用；
4. 当前本地验收只启用 `provider=nexweave.local`、`externally_hosted=false`。它是确定性无网络 Provider，不是外部 LLM；
5. ModelProfile classification ceiling 必须覆盖所有输入，`HIGHLY_RESTRICTED` 不得路由到 externally hosted Profile。

Compile Center 通过真实 API 选择上述固定版本和 FULL/INCREMENTAL/SOURCE_SCOPED/RECOMPILE 模式。失败重试创建新的、可审计的 RECOMPILE Job，不改写旧 Job。

## 3. Wiki 工作台

- AI 只生成 `generated_sections`；人工编辑只通过带 ETag 的 PATCH 创建新 PageVersion；
- `protected_sections` 在重编译时原样保留；数据库 trigger 禁止更新/删除历史 PageVersion；
- 版本选择、diff、链接/反链、评论、关注和 SourceAnchor EvidenceCandidate 元数据来自真实 API；
- 所有页面状态仍为 DRAFT；Consumer 默认不能读取。

## 4. 验证

```bash
.venv/bin/ruff check .
.venv/bin/mypy
NEXWEAVE_TEMPORAL_TEST_ENDPOINT=127.0.0.1:7233 \
  NEXWEAVE_TEMPORAL_TEST_NAMESPACE=nexweave-dev \
  .venv/bin/pytest -q
npm --prefix apps/web run format:check
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test
npm --prefix apps/web run build
.venv/bin/python scripts/verify_m5.py --base-url http://127.0.0.1:8000/api/v1
```

迁移检查读取 `.env` 后应把 Compose 内部主机名 `postgres` 替换为宿主 `127.0.0.1`，脚本只创建并自动删除命名唯一的一次性数据库：

```bash
set -a
source .env
set +a
NEXWEAVE_DATABASE_URL="${NEXWEAVE_DATABASE_URL/postgres:5432/127.0.0.1:5432}"
export NEXWEAVE_DATABASE_URL
PYTHONPATH=apps/api/src:packages/domain/src:packages/application/src:packages/contracts/src \
  .venv/bin/python scripts/check_migrations.py
```

## 5. 诊断

- CompileJob `MODEL_PROVIDER_UNAVAILABLE`：所选 Profile 不是 `nexweave.local`，当前没有外部 adapter；
- `COMPILE_SCHEMA_NOT_PUBLISHED`：必须选择已发布 SchemaVersion；
- `COMPILE_SOURCE_NOT_READY`：SourceVersion 没有 active parsed result；
- `MODEL_CLASSIFICATION_DENIED`/`MODEL_EGRESS_DENIED`：模型密级或外发策略拒绝；
- `MODEL_BUDGET_EXCEEDED`：输入超过 Profile 的 `max_input_units`；
- `VERSION_CONFLICT`/`WIKI_VERSION_NOT_CURRENT`：刷新 Wiki 页面后基于最新 ETag/版本重试。

## 6. 安全与停止边界

- ModelInvocation 只保存 checksum、units、latency、cost 和稳定引用，不在日志/事件中复制 Raw；
- EvidenceCandidate 绑定 VALID SourceAnchor；Wiki API 仅暴露 Evidence 元数据，不直接暴露原文；
- Broker 发布、外部 LLM、M6 Review、正式 Evidence、Release、Query、GridCrew 与 RCA 均未实现；
- M5 已正式验收；当前停止在已验收 M5，未明确下发 M6 前不得继续。
