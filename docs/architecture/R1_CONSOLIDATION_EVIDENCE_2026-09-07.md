# R1 Consolidation 核查证据 — 2026-09-07

> 作用：支撑 [R1/R2 架构评审](R1_CONSOLIDATION_R2_LIVING_KNOWLEDGE_REVIEW.md)。这是本轮只读核查与测试记录，不是 R1/M9 业务验收报告。

## 1. 审查基线

- 工作区：`/Users/joiefu/Project/NEXWEAVE`。
- HEAD：`51fa9fd9d4e3327dfe3db4125fcecb1d8660808c`。
- 评审输入包括大量 tracked modified / untracked 的 M3—M9 实现与文档；未 reset、stash、清理、提交或 push。不能把未提交的新领域/契约文件视为“不存在”。
- 当前指令只授权检查和规划。M9/M9-FE 旧任务书用于现状评估，不等于本轮执行其模型配置或实施任务。未委派子代理。
- 检查时存在更新于同一天的前端工作：最新 OPEN_QUESTIONS 的 OQ-FE-VISUAL-002 与当前 `tokens.css` 已恢复紫/青配色；较早设计系统文档不能覆盖这条已记录决定。

## 2. 权威资料与代码定位

路径均相对仓库根目录；行号为本轮阅读时的位置，用户后续修改可能移动。

| 证据 | 位置 | 支撑内容 |
|---|---|---|
| 当前 M9 范围 | `docs/development/tasks/11_NEXWEAVE_M9_Equipment RCA领域包、纵向闭环与联合试点验收任务书.md` | 公开资料技术试点、专家/阈值/真实评审 P0，GridCrew 延期 |
| M9 已知结果 | `docs/development/reports/NEXWEAVE_M9_执行与验收报告.md` | 368 ClaimCandidate / 377 EvidenceCandidate / 9 RelationCandidate；该试点正式 Claim/Review/Release 为 0；不能当 P-101 数据 |
| 架构主干 | `ARCHITECTURE_BASELINE.md`、`PRODUCT_BASELINE.md` | 模块化单体、独立 Worker、单一 Schema、固定 Release、Gateway/Connector |
| 治理与追踪 | `AGENTS.md`、`OPEN_QUESTIONS.md`、`docs/governance/REQUIREMENTS_TRACEABILITY_MATRIX.md` | 已验收范围与待决、质量/安全/证据责任 |
| 语义权威 | `docs/architecture/adr/ADR-0022-m4-semantic-model-schema-authority-pack-composition.md` | 不新增 OntologyVersion、确定性 Pack 组合 |
| Pack 实现契约 | `docs/architecture/adr/ADR-0023-m4-pack-implementation-contract.md` | JSON-only、签名、stable key、受限 UI/DSL |
| 编译、证据、发布 | `docs/architecture/adr/ADR-0024-m5-compile-wiki-model-contract.md`、`ADR-0025-m6-claim-evidence-conflict-review.md`、`ADR-0026-m7-quality-release-query-projection.md` | 候选/正式分离、审核、发布不可变与抽取式 Query |
| 集成/图导航 | `docs/architecture/adr/ADR-0027-m8-connector-obsidian-boundary.md`、`ADR-0028-m8-wiki-bidirectional-link-graph.md` | 只读文件 Connector、Obsidian 草稿、Wiki 图与 Release 图分开 |
| 模型端口 | `packages/application/src/nexweave_application/ports.py:116` | 请求锁定 Prompt/Schema/segments；端口只有 structured_output / embedding，没有时序请求 |
| 实际 Provider | `apps/api/src/nexweave_api/model_gateway.py:24`、`:69` | LocalModelGateway；本地结构编译与 16 维哈希 embedding |
| 仓储组装 | `apps/api/src/nexweave_api/knowledge_repository.py:53`；`apps/api/src/nexweave_api/app.py:56` | 具体 LocalModelGateway 默认注入；跨域继承至 IntegrationRepository |
| Semantic 契约 | `packages/contracts/src/nexweave_contracts/semantic.py:25`、`:92`；`base.py:4` | 属性/关系声明、无 signal/profile 声明；extra=forbid |
| 组合纯逻辑 | `packages/domain/src/nexweave_domain/semantic.py:346` | 明确声明块、确定性组合、冲突拒绝；新增字段不能仅靠 UI JSON 生效 |
| Evidence 表约束 | `migrations/versions/0007_m6_claim_evidence_review.py:99` | evidence_records 要求 source_anchor_id；不直接接 ForecastArtifact |
| 实体/页面版本 | `migrations/versions/0006_m5_compile_wiki.py`；`knowledge_repository.py` | stable entity、追加版本、保护区；避免把测点刷新写成 Wiki 修订 |
| 不可变正式对象 | `migrations/versions/0007_m6_claim_evidence_review.py`、`0008_m7_quality_release_query.py` | Claim/Evidence/Release 等 immutable triggers |
| 当前 Query | `apps/api/src/nexweave_api/release_repository.py:1900` | 固定 Release、关键词/哈希向量、抽取式合成、Citation 与拒答；业务 filters 待复核 |
| 当前 Graph | `apps/api/src/nexweave_api/release_repository.py:2207` | Release 范围关系；节点从当前实体行读取、起点成员资格待核；SQL 2000 上限与输出 500 上限 |
| 文件 Connector | `apps/api/src/nexweave_api/connector_provider.py:45` | FILESYSTEM/S3/WEB_REST/GIT；返回文件字节，无工业时序专用契约 |
| Workflow | `workers/kernel/src/nexweave_worker_kernel/workflows.py`、`activities.py` | 可靠编排与 Activity 分离、历史定义保留 |
| Pack | `domain-packs/equipment-rca/{manifest,semantic,authoring,evaluation}.json` | 1.0.0、Ed25519、声明式 RCA；复用 nexweave.io/equipment，无 P-101 现场绑定 |
| UI 路由与实际页面 | `apps/web/src/App.tsx:44`；`SchemaStudio.tsx`、`WikiWorkbench.tsx`、`WikiLinkGraph.tsx`、`M7Knowledge.tsx`、`IntegrationCenter.tsx` | 已有工作台可增量；无独立设备运行页面 |
| UI 原型/现状 | `docs/product/nexweave/NEXWEAVE_高保真交互原型_V1.0.html`；`docs/design/FRONTEND_DESIGN_SYSTEM.md`；`FRONTEND_UI_AUDIT.md` | 原型文本含 RCA 空间/助手，但演示问答是脚本；不能据此判断真实动态能力 |
| 历史视觉证据 | `docs/development/evidence/m9-fe/system-refactor-2026-09-07/wiki-1920x1080.png` | 本轮查看既有 Wiki 三栏空态截图；不是本轮新 UI 截图，也不代表最新 token 效果 |
| 原 R2 | `docs/development/tasks/12_NEXWEAVE_M10_企业级治理、多空间运营与精细权限任务书.md`、`13_NEXWEAVE_M11_高级检索、知识图智能与持续评估任务书.md`、`14_NEXWEAVE_M12_高可用、灾备、国产化与规模性能任务书.md` | 企业治理、高级检索/持续评估、生产部署责任继续保留 |

## 3. 当前运行环境与数据库：只读结果

首次普通沙箱访问 Docker socket 被系统权限拒绝；随后经工具审批的只读检查成功。没有启动/停止/重建容器，没有运行迁移或业务写入脚本。

容器快照：API/Web/PostgreSQL/Redis/RustFS/Temporal/ClamAV running 且 healthy；该次列表未出现业务 Worker、health Worker、Parser Worker 或 Parser sandbox。仅据此判断**当时**不能确认完整工作流可执行，不把它解释为历史从未运行。

数据库通过现有 API 容器的 Settings/Database 建立连接，仅执行 SELECT，事务显式 `READ ONLY`。不输出连接字符串、凭据、业务文本、身份名单或测点数据。

| 只读查询 | 结果 |
|---|---|
| alembic_version | `0009_m8` |
| SourceVersion 数量 | 90 |
| SchemaVersion 数量 | 56 |
| Claim 数量 | 4 |
| Release 数量 | 0 |
| QueryAnswer 数量 | 0 |
| ModelProfile provider 分组 | `nexweave.local`：22 |
| public schema 启用 rowsecurity 表数量 | 0 |
| 动态领域表 | 表清单未见 Signal/Observation/Forecast/Hypothesis 专用表 |
| 约束核查 | source_versions_protect_raw、source_anchors_protect、schema_versions_protect、claims/evidence_records/relations/releases/release_items/citations/query_answers immutable，以及 audit_logs append_only 等触发器存在 |

没有核验每一触发器在恶意 SQL 下的执行效果，没有读取全部业务行或证明每条记录有效。此次结构与数量证据不能覆盖远程或过去隔离测试库，也不能证明生产成熟度。

## 4. 本轮实际执行的测试

```text
.venv/bin/python -m pytest -q tests/architecture tests/contract packages/domain/tests packages/contracts/tests apps/api/tests/test_m4_semantic_security.py apps/api/tests/test_m5_model_gateway.py apps/api/tests/test_m8_connector_provider.py workers/kernel/tests/test_workflow_definitions.py -m 'not integration'
结果：88 passed in 2.20s

pnpm --filter @nexweave/web test -- --run
结果：6 files / 23 tests passed

pnpm --filter @nexweave/web typecheck
结果：tsc -b --pretty false，退出码 0
```

前端测试包含预期 401/503 失败场景的 stderr 诊断，不是测试失败。本轮数量 23 来自当前工作区，不沿用较早报告的 22。

未执行：全量 make check、全量后端测试、远程 CI、真实模型/工业 benchmark、写入式 R1 E2E、迁移升级/回滚、生产隔离渗透、性能/HA/DR、新版 UI 实时浏览与视觉验收。此次仅文档交付，不为低影响文档变更新增镜像实现的测试。

## 5. 模型资料：截至本次检索

- [Amazon Chronos-2 模型卡](https://huggingface.co/amazon/chronos-2)：模型身份、能力、context/horizon、部署与模型许可；见评审 ④。
- [Amazon 官方推理库](https://github.com/amazon-science/chronos-forecasting)：predict_df/future_df/quantile_levels 用法；见评审 ④。
- [Chronos2 pipeline 源码](https://github.com/amazon-science/chronos-forecasting/blob/main/src/chronos/chronos2/pipeline.py)：cross_learning、长 horizon、分位输出映射；见评审 ④。
- [DataFrame 转换源码](https://github.com/amazon-science/chronos-forecasting/blob/main/src/chronos/df_utils.py)：未来时间网格校验与协变量映射；见评审 ④。
- [Google TimesFM 官方库](https://github.com/google-research/timesfm)：逐版本能力与代码/权重许可区别；见评审 ④。

上述为在线文档分支/模型卡，不是已锁定的部署制品。实施必须固定源码、包、权重与镜像摘要，再以实际能力测试重验；不把在线 README 的 benchmark 宣传变成本项目测试结果。

## 6. 本轮文件与停止边界

- 新增 `R1_CONSOLIDATION_R2_LIVING_KNOWLEDGE_REVIEW.md`：十项完整规划与提案需求追踪。
- 新增本证据文档。
- 新增 `adr/ADR-0031-living-knowledge-extension-proposal.md`：状态 Proposed；不修改既有 Accepted ADR。
- `OPEN_QUESTIONS.md`：仅追加 R1 收口与 Living Knowledge 待决/冲突记录，保留既有内容。

无应用代码/历史迁移/Pack 字节/旧任务书更改，无新依赖、数据导入、外部发布或提交。停止在评审与规划；未执行 M9.5/M10。

文档检查：主报告十项章节齐全；三份新增 Markdown 的本地链接均可解析、代码围栏成对；`git diff --check` 通过。OPEN_QUESTIONS 原本已有未提交改动，当前相对 HEAD 的总 diff 不代表本轮追加量，本轮只追加 Living Knowledge 节。

## 7. 关键输入文件指纹

用于识别本轮审阅的工作区版本，不代表 Git 已提交；不含凭据文件。

| 文件 | SHA-256 |
|---|---|
| `packages/application/src/nexweave_application/ports.py` | `fcac681eb43559cecb0e4f259ee7d1e522878a494a5ec849a1ded581c3f2eb1b` |
| `apps/api/src/nexweave_api/model_gateway.py` | `e76e7f9bc93910eb43ae824b7fbd95eeeb4c71a53c25e8aa4fb55c645cd75bf2` |
| `apps/api/src/nexweave_api/release_repository.py` | `5fa6abbe763eebf43deb309e4b6839eb8b663973302fd9a4b3f293912c4b7d79` |
| `apps/api/src/nexweave_api/knowledge_repository.py` | `11a3060038d55ec8d68c612cf03e1bc1b28a9bfca4ec145eb33d949facf6cd9d` |
| `packages/contracts/src/nexweave_contracts/semantic.py` | `a8ebc1db1e4570bcf94048eb1c602cba226014e4e829a88722a57916cefd9c88` |
| `domain-packs/equipment-rca/manifest.json` | `2006b3c19be06815406df57012dc9209cbabee108ad4df0314b0e52feec9cf6f` |
| `apps/web/src/App.tsx` | `a7ab55421b106b6a2164cf26e92f0e88c1bf320c775ffb964b7cba9983e50555` |
| `apps/web/src/styles/tokens.css` | `5db538d545d8840250ab4893defb6dce8015b3aa8e1a5b5da62d917d3e4a82f0` |
