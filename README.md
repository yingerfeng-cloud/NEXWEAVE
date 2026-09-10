# NEXWEAVE｜织界

NEXWEAVE 是面向企业专业知识的 LLM 原生知识编译、审核、发布与服务平台。

当前仓库已正式验收 M1—M8。用户于 2026-09-01 正式下发 **M9 Equipment RCA 领域包与试点**；签名声明式 Pack、9 份/610 页 NTSB 公开资料准入和 4 份代表性 Pack→Source→Compile 技术试点已实施。ADR-0030 将 GridCrew 暂不开发及联合试点延期；专家身份、批准阈值和真实 Review/Release 仍未完成，因此 M9 不能宣称通过。

## 当前状态

- Release 基线：R1 = M0—M9；
- 最近由用户正式验收的 Milestone：M8（2026-08-31）；当前 M9.5 阶段 D 验收与可信边界收口已于 2026-09-10 完成本地技术验证（11F / ADR-0036，不以 M9 验收为前置）；
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

阶段 A 运行手册见 [`docs/development/STAGE_A_RUNBOOK.md`](docs/development/STAGE_A_RUNBOOK.md)。当前预测是合成数据上的真实 Chronos-2 条件推理，不代表现场验证，也不会生成 Evidence 或已发布知识。

阶段 B 可在 Wiki 的“运行与未来 · 预览”中新增运行数据绑定、预检并比较同窗口场景；前提为已有受控 CSV、已发布时序 Schema 和知识对象。见 [阶段 B 手册](docs/development/STAGE_B_RUNBOOK.md)及[执行报告](docs/development/reports/NEXWEAVE_阶段B_自主运行执行报告.md)。停止在 B，不进入 C/M10。

阶段 C 已按后续授权完成：预测结果下方可选择固定知识版本，检索已发布依据并查看原文定位。见 [阶段 C 手册](docs/development/STAGE_C_RUNBOOK.md)及[执行报告](docs/development/reports/NEXWEAVE_阶段C_知识回接执行报告.md)。API/本地预测进程版本为 `0.9.5-c1`；当前停止在 C，不进入 M10。

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
