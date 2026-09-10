# NEXWEAVE M9 执行与验收报告

## 1. 总体结论

- 阶段：不通过（本地技术交付、公开资料准入与 Source→Compile 技术试点已实施；专家验收仍受 P0 阻塞）
- 是否满足进入下一阶段条件：否
- Git 基线：工作区包含用户既有 M3—M8 未提交变更和本次 M9 增量；未提交、未 push

## 2. 实际完成范围

- 已冻结 ADR-0029，明确声明式 RCA Pack、辅助知识分析、安全证据、真实试点与 GridCrew 联合边界。
- 已交付签名 `equipment-rca-pack@1.0.0`：12 个领域类型、10 个属性、12 个 Evidence-aware Relation、术语/同义词、3 个模板（含受限 Prompt）、6 条 Lint、UI 元数据和 7 个标准问题。
- 已验证 `core-pack`、Equipment RCA Pack 与 `maintenance-pack` 确定性组合，公共 Equipment 不重复；所有 3 条因果 Relation 强制 Evidence。
- 已交付明确 `SYNTHETIC` 且 `pilotEvidence=false` 的技术 fixture、运行手册和空白联合验收模板。
- 已按 ADR-0030 取得并逐份准入 9 份/610 页 NTSB 官方调查报告，完成文本提取、关键结论页目检和第三方视觉元素排除清单。
- 已选择 4 份跨海事/航空/管道/铁路的代表性报告，真实注册并安装签名 Pack，保留 Raw 安全拒绝事实，以排除指定页的文本派生 SourceVersion 完成 4 个 CompileJob。
- 已形成 368 个 ClaimCandidate、377 个 EvidenceCandidate 和 9 个 RelationCandidate；外部模型、正式 Claim、ReviewCase 与 Release 均为 0。
- 已修复 Web 入口 1 MB 上传限制和 M4 Pack evaluationSuites 持久化遗漏 M7 `created_by` 的跨 Milestone P0。
- GridCrew 暂不开发、联合试点延期，不再是 M9 P0 或交付项，也未声称完成。
- 未实施或声称公开资料 RCA Release、专家评审、真实/内网模型或批准指标。

## 3. 新增或修改文件

- `docs/architecture/adr/ADR-0029-m9-equipment-rca-pack-and-pilot-boundary.md`：M9 决策与证据边界。
- `domain-packs/equipment-rca/{manifest,semantic,authoring,evaluation,publisher-public-key}.json`：签名 Pack、领域声明和标准问题集。
- `domain-packs/equipment-rca/examples/synthetic-rca-case.json`：不可作为试点证据的技术 fixture。
- `packages/domain/tests/test_m9_equipment_rca_pack.py`、`scripts/verify_m9_pack.py`：自动验证与可复现摘要。
- `docs/development/M9_RUNBOOK.md`、`docs/development/M9_PILOT_ACCEPTANCE_TEMPLATE.md`：真实执行顺序、准入、指标和故障记录模板。
- `docs/architecture/adr/ADR-0030-m9-public-rca-corpus-and-gridcrew-deferral.md`：公开候选语料使用边界和 GridCrew 延期决策。
- `docs/reference/domain/rca/PUBLIC_SOURCE_CATALOG.md`、`PUBLIC_SOURCE_ADMISSION_REPORT.md`、`public-source-accession-manifest.json`：9 份官方来源、逐页解析/视觉排除、SHA-256 和准入状态。
- `scripts/verify_m9_public_pilot.py`、`docs/development/evidence/m9-public-pilot/TECHNICAL_PILOT_RUN_2026-09-02.md`：可复现的真实 Pack/Source/Compile 技术试点和运行事实。
- `apps/web/nginx.conf`：受控上传上限与 API 默认 100 MB 上限对齐。
- `apps/api/src/nexweave_api/semantic_repository.py`、`apps/api/tests/test_m4_semantic_security.py`：Pack evaluationSuites 持久化兼容修复与回归测试。
- M9 任务书、AGENTS、产品/架构/状态/索引、Open Questions、ADR 索引、GridCrew 基线、需求追踪、影响矩阵、CHANGELOG、Makefile 和本报告：同步当前授权与 P0 状态。
- 全局格式门禁机械格式化 13 个既有 M6—M8 Python 文件；未改变其业务语义。

## 4. 领域对象、API、事件和 Workflow 变更

- 新增：只新增 Pack 内声明式领域类型/关系/术语/模板/Lint/问题集和技术试点验证脚本。
- 修改：修复既有 M4 Pack 持久化实现，向 M7 evaluation_suites 写入既有必填审计 actor；无核心对象、API、事件或 Workflow 语义变更。
- 兼容性影响：沿用 M4 Pack v1alpha1 与 M7 EvaluationSuite；安装仍只生成 DRAFT SchemaVersion。
- ADR：ADR-0029、ADR-0030。

## 5. 测试与验证

- `scripts/verify_m9_pack.py`：通过；签名与 3 个内容 checksum 有效，组合 checksum 为 `sha256:c4bd5d761cff0a3af7349b1996611090c3fe3d08a4e0406440eea307b7b1ee33`。
- `pytest -q packages/domain/tests/test_m9_equipment_rca_pack.py`：6 passed。
- `make check PYTHON=.venv/bin/python`：通过；Python 120 passed/5 integration deselected，契约 27 passed，Web 22 passed，Ruff format/lint、strict mypy（83 source files）、ESLint、TypeScript、SDK 和生产构建通过。
- M3/M4 Workflow replay + parser sandbox 集成子集：3 passed；首次在受限沙箱运行因回环网络/端口权限失败，授权本机网络后原命令通过。
- Compose：API、Web、PostgreSQL、Redis、RustFS、Temporal、Parser sandbox、ClamAV 均 healthy；三个 Worker running。
- `docker compose exec -T api python scripts/check_migrations.py`：一次性数据库 `0001→0009→0008→0007→0009` 通过，M0—M4 sentinel 和 M8 表/pgvector 投影保留。
- JSON 解析、Secret pattern scan 与 `git diff --check`：通过。
- 公开资料：9 个下载对象均验证为 PDF，共 610 页；manifest 中 URL、文件名、source ID 与 SHA-256 唯一，文件 checksum 与 manifest 一致。
- 逐份准入：610/610 页可提取文本；9 个关键结论页目检通过，第三方视觉元素/低文本页已记录排除。
- `scripts/verify_m9_public_pilot.py`：经修复后的 `:8080` Web 入口和隔离租户真实运行通过；签名 Pack 安装 `ACTIVE`，4 个 Raw/派生/Compile 三段式审计链完整。
- 试点统计：368 ClaimCandidate、377 EvidenceCandidate、9 RelationCandidate；4 个 Compile 均 `SUCCEEDED`，`external_llm_called=false`，formal Claim/ReviewCase/Release 均为 0。
- `pytest -q apps/api/tests/test_m4_semantic_security.py packages/domain/tests/test_m9_equipment_rca_pack.py`：12 passed；相关 Ruff、strict mypy 通过。
- Web 镜像与 Worker 镜像重建成功；最大 6.56 MB PDF 经 Web 代理上传，413 已关闭。
- 未执行：专家盲审、正式 Evaluation/Release/Query、真实/内网模型、GridCrew 对端、生产性能/HA/DR；均不得由技术候选链替代。

## 6. 数据库与迁移

- 迁移文件：无。M9 Pack 使用既有 M4 表和契约。
- 回滚验证：Pack 缺席时 core + maintenance 仍可组合；未修改历史迁移。
- 数据兼容性：历史 SchemaVersion/PackVersion/Release 不变。

## 7. 安全、权限、审计与证据检查

- Pack JSON-only、`executableContent=false`、Ed25519 签名；私钥未保存在仓库。
- 合成 fixture 明确不可作为试点证据；公开原始 PDF 未进入 Git。Raw PDF 因加密标志被解析策略拒绝但事实保留，派生文本排除指定视觉页后另建 SourceVersion；外部模型保持禁用。
- Web 代理上限提升没有放宽 API 的大小、内容类型、checksum、ClamAV 或解析安全策略。
- 平台运行时代码扫描无 `equipment.rca/` 或 `kks-code` 专用分支。
- 真实知识仍必须经过既有权限、审计、Evidence、Review 和 Release 门禁。
- 未增加第三方依赖、凭据、数据库表、API、事件或 Workflow；无需新的许可证或供应链例外。

## 8. 风险与遗留项

- P0：缺少专家名单、批准阈值和对候选知识的真实评审/签署记录；因此不得生成正式 RCA Release。
- 已关闭：公开资料逐份准入、4 份代表性 Source→Compile、Web 大文件上传 413、真实 Pack 安装及 evaluationSuites 跨版本持久化缺陷。
- P1：客户侧 RCA/IOE/LOE/手册仍未提供；另外 5 份已准入报告尚未纳入扩展试点。
- DEFERRED：GridCrew 暂不开发，联合试点延期；不属于 M9 P0 或验收范围。
- P1：真实/内网模型 Provider、生产 OIDC/Secret Provider 和目标环境 E2E 未执行。
- P2：规模性能、HA/DR 和专门崩溃窗口继续按后续门禁跟踪。

## 9. 需求追踪更新

- 已完成：M9 Pack 技术制品、跨 Pack 组合、标准问题集和平台无领域分支验证。
- 已完成本地技术：NXW-PACK-002、公开资料 Source→Compile 候选链。
- 部分完成：NXW-KQ-001、NXW-KQ-002。
- 未覆盖：专家 Review→Evaluate→Release→Query；GridCrew 联动已延期。

## 10. 停止声明

已停止在 M9，未自行进入下一 Milestone。当前报告不构成 M9/R1 公开资料技术试点验收通过；GridCrew 联合试点已延期且未完成。
