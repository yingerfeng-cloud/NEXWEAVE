# NEXWEAVE｜织界

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台。

R1 软件功能已于 2026-09-14 由用户正式验收，验收标签为 `r1-software-accepted-20260914`。该记录不等同 Equipment RCA 专家、批准阈值、真实领域评审或工业效果验收；这些事项继续独立开放。GridCrew 集成与联合试点按 ADR-0030 延期。

## 当前状态

- Release 基线：R1 = M0—M9；
- 当前软件验收基准：2026-09-14 R1 软件验收，包含 M9.5 与阶段 A—D 及补修，不改变 R1=M0—M9 的里程碑归属；
- 当前迭代：2026-10-17 独立 Review 的 R1 整改 B 批，代码标识 `0.9.5-r1fix-b1` / `R1_REVIEW_B`，依据 ADR-0038/0039；[整改追踪](docs/development/reports/R1_Review_整改追踪_20261017.md)记录实际结果。Web 自然问句评估50%仍阻止发布，继续C修复；此版本没有替换验收标签；
- 已实现业务边界：M1 平台、M2 Workflow、M3 Source/Parse、M4 Schema/Domain Pack、M5 Compile/Wiki、M6 Claim/Evidence/Review、M7 Quality/Release/Graph/Query、M8 Connector/Obsidian/Wiki 图谱，以及 M9 Equipment RCA Pack 技术制品；
- 技术基线：Python 3.12/FastAPI、React/TypeScript、Temporal、PostgreSQL/pgvector、RustFS/S3、Redis；
- 停止边界：不得自行进入 M10；GridCrew 集成按用户指令延期且未实现，公开资料准入和 Source→Compile 已完成，专家 Review/Evaluation/Release/Query 仍为 P0。

## 本地启动与验证

```bash
make dev-up
make dev-status
make verify
make verify-m2
make verify-m4
.venv/bin/python scripts/verify_m9_pack.py
.venv/bin/python scripts/verify_stage_a_r1.py
```

`make dev-up` 启动 Compose，并在已安装锁定的预测运行环境/模型时恢复唯一的本地预测 worker；重复执行不重复 worker。`make dev-down` 先停止该 worker 再停止 Compose，不删除数据卷。未安装可选模型时明确报告离线，不影响 R1 启动。

阶段 A 运行手册见 [`docs/development/STAGE_A_RUNBOOK.md`](docs/development/STAGE_A_RUNBOOK.md)。历史报告中的 Chronos-2 合成推理与本次整改验证分开；本次 A 批未验收模型效果。条件预测不生成 Evidence 或已发布知识。

阶段 B 可在 Wiki 的“运行与未来 · 预览”中新增运行数据绑定、预检并比较同窗口场景；前提为已有受控 CSV、已发布时序 Schema 和知识对象。见 [阶段 B 手册](docs/development/STAGE_B_RUNBOOK.md)及[执行报告](docs/development/reports/NEXWEAVE_阶段B_自主运行执行报告.md)。该句对应历史阶段 B，当前边界以上文为准。

阶段 C 已按后续授权完成：预测结果下方可选择固定知识版本，检索已发布依据并查看原文定位。见 [阶段 C 手册](docs/development/STAGE_C_RUNBOOK.md)及[执行报告](docs/development/reports/NEXWEAVE_阶段C_知识回接执行报告.md)。该报告的 `0.9.5-c1` 是历史执行版本，当前代码标识以 `packages/contracts/src/nexweave_contracts/runtime.py` 与运行 API 为准。

M9 边界与验证见 [`docs/development/M9_RUNBOOK.md`](docs/development/M9_RUNBOOK.md)。

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
