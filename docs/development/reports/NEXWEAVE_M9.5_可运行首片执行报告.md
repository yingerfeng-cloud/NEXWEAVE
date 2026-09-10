# M9.5 可运行首片执行报告

日期：2026-09-08。授权：用户 2026-09-07 明确要求不以 M9 验收为开发前置，先开发 M9.5 并跑起来。依据：11B 任务书、ADR-0032。状态：**本地技术首片已跑通；未宣称完整 M9.5 工业试点验收或 R2 完成**。

## 交付结果与访问

打开 http://localhost:8080/wiki?view=living ，使用已有本地开发身份登录，选择 **P-101 运行知识演示 · 已跑通**。在“场景与模型”中选择“**两小时负荷70%升至95% · chronos2 · SUCCEEDED**”。相同运行态预览也接入现有 Graph、Ask、Schema Studio 和集成路由，通过“知识与治理 / 运行与未来”切换。

此次运行使用**明确标记的合成数据**：1440 个一分钟记录点，最近 720 点作为模型历史，预测 120 步。实际通过受控 Source 上传、ClamAV、解析、Schema 发布、规则编译建立 P-101 实体/Wiki，再绑定 CSV。不存在真实工业测点、现场阈值批准或专家诊断记录。

| 场景 | Provider | 两小时末端 P50 | 示例阈值条件 |
|---|---|---:|---|
| 负荷保持 70% | Chronos-2 | 58.183475 °C | 未匹配 |
| 两小时内负荷 70% → 95% | Chronos-2 | 61.026730 °C | P90 触及演示 60°C 阈值 |
| 持久性基准 | Persistence | 58.184800 °C | 未评估；仅 P50，忽略协变量 |

以上数值来自真实本地模型执行，不是固定前端 JSON。升级推理依赖后重新跑通，数值一致；两个 Chronos 场景生成独立不可变制品。条件预测不等于因果推断，P90 越阈不等于故障概率，示例规则不得用于现场报警。结果清单见同目录 `M9.5_运行证据.json`。

## 实际实现范围

- 新增 provider-neutral `TimeSeriesModelProvider`、CSV Connector 和 allowlisted `ForecastModelGateway`；Chronos-2/Persistence 分别适配。API、领域层和 Workflow 不导入 Torch SDK。
- Schema 声明扩展 `signalDefinitions`、`forecastProfiles`，冻结 Target、Past Covariate、Known Future Covariate、频率、单位与工况上下文；旧声明在新增字段为空时保持原序列化内容。修改/删除既有时序定义属于 breaking change。
- `SignalBinding` 固定同一知识空间的实体、已发布 SchemaVersion 和已扫描 SourceVersion；继承输入密级，保存源/Schema checksum 和实体快照。
- `Observation / OperationalContext / ForecastContext` 在首片作为冻结的 JSON 值对象保存；`PotentialEvent / Hypothesis / Risk Narrative` 为 ForecastArtifact 内的派生评估，不是独立已发布知识表。
- 新增 `signal_bindings / forecast_runs / forecast_artifacts` 三表、组合外键、不可变触发器；ForecastRun 使用独立 Temporal 队列，Activity 执行存储读取、模型推理和持久化。上下文冻结，完成/失败可见，输出有 S3 原始制品及 SHA-256。
- 重新验证发起身份、当前空间权限和源可用性；写入审计及 outbox。相同幂等键返回同一任务，重复活动完成检查终态，不改写已完成制品。
- 页面呈现输入历史、P10/P50/P90、场景参数、任务状态、Potential Event、待核实解释与来源摘要；Graph 首片为产物来源链视图，尚未改动 R1 图投影。Wiki 关联回既有实体页面；Ask 首片为结构化条件预测界面，明确未实现自由文本 LLM 路由。
- 修复空间选择器只读取前 50 个空间的问题，新增分页回归测试；否则新建演示空间不可见。

## 核心边界与尚未完成项

1. 没有将 ForecastArtifact 写成 Evidence、Claim、Observed Fact 或 Release。当前无适用已发布知识，页面明确“未使用已发布知识依据”；Wiki 草稿链接不充当证据引用。
2. 可选 `release_id` 当前只记录并鉴权固定 Release 引用；**尚未实现基于发布快照的 RCA/规程/历史案例检索和风险叙述引用合成**。完整知识回接仍是后续 M9.5 加固项。
3. Equipment RCA `living/temporal-declarations.json` 是声明式开发 overlay，使用现有 Schema 发布通路。没有修改或冒充重新签发原 Pack 1.0.0；新版签名 Pack 注册/安装留待后续。
4. 集成首片为受控版本化 CSV，无 PI/SCADA/Historian 实时轮询；CSV 绑定创建可用 API，页面尚无完整可视化绑定向导。
5. 无工业 Benchmark、概率校准、跨设备泛化或因果效果声明。保持 TimesFM、私有模型及专业工业模型的替换接口；当前只实现 Chronos-2 与 Persistence。
6. 本地独立 CPU worker 已启动。生产部署、并发/配额、取消/恢复、孤立对象清理、自动补发 QUEUED 任务、跨租户专项压测与长期保留策略尚未完成。API→Temporal 投递失败时需以同一幂等键重试，不能声称已具备无人值守调度运维能力。
7. 旧 `/version` 仍表示 R1 基线版本；新增时序接口/产物用 `nexweave.forecast-artifact/1`、独立 Workflow 名和 ADR-0032 识别此次预览。

## 验证结果

| 检查 | 实际结果 |
|---|---|
| 领域/契约/OpenAPI 与相关模型网关回归 | 88 passed；包含 12 个新增时序用例 |
| Python 严格类型检查 | 92 个模块通过 |
| 新增/受影响 Python lint | 通过 |
| Web 测试 | 24 passed，含空间分页回归 |
| Web 类型、lint、构建 | 通过；本地 Compose API/Web 已构建启动 |
| Chronos 模型 | 固定权重/配置校验；升级后真实 CPU 推理及三个 E2E 场景成功 |
| 权限与负向 | 无空间权限身份访问 Binding/Run/Artifact 均 403；缺失 future input → FAILED、无 Artifact；同幂等键不同载荷 → 409 |
| 制品完整性 | API 内容、S3 字节内容与 SHA-256 相符 |
| 不可变 | 三表受保护记录的 no-op UPDATE 均拒绝，测试事务回滚 |
| 数据库迁移 | 实际库升到 0010_m95；独立临时库升级、降级至 0009_m8、继续旧链路降级/再升级，旧 sentinel 数据保留 |
| 页面 | 浏览器核验对象、合成标记、成功场景、曲线和追溯区；未宣称所有尺寸/全部旧页面完整视觉回归 |
| 依赖审计 | 初次发现 13 个通告；升级 Torch/Transformers 后对完整 forecast.lock 重审：No known vulnerabilities found |

上表是本地验证，不等于远程 CI、安全认证或独立专家验收。完整原 R1 业务 E2E 没有全部重跑。

发现并保留的既有问题：CSV 上传完成响应的 X-Trace-Id 与请求 traceparent 不一致。验证客户端将该差异写入 `.nexweave-data/m95-trace-mismatches.jsonl`，不把追踪一致性列为通过；没有为此次预览修改 R1 上传语义。

## 变更文件与迁移影响

- 授权与契约：`AGENTS.md`、11B 任务书、ADR-0032、`OPEN_QUESTIONS.md`、依赖基线、需求矩阵；`packages/contracts/.../forecast.py`、`semantic.py`、schema_export、生成的 JSON Schema/OpenAPI。
- 领域与适配：`packages/domain/.../forecast.py`、`semantic.py`、`packages/application/.../forecast_ports.py`；API 新增 forecast_repository/routes/gateway/execution，调整 app/settings/workflow_gateway 注册。
- Worker：`workers/kernel/.../forecast_workflow.py`、`forecast_main.py`。没有改动旧 Workflow 定义。
- 数据：新迁移 `0010_m95_forecast.py`；没有编辑旧迁移。新增记录、技术发布身份、演示空间与失败测试记录保留；未删除既有用户数据。
- 前端：`LivingKnowledge.tsx`、`livingTypes.ts`、`living.css`，App/api 适配与 api.test 分页用例。
- 运行/验证：`fetch_m95_model.py`、`run_m95_worker.py`、`verify_m95.py`、`verify_m95_guards.py`、迁移检查脚本；新增 domain 时序测试、requirements/forecast.txt 与 forecast.lock。
- 领域声明：`domain-packs/equipment-rca/living/`。模型权重、虚拟环境、日志、运行数据均在被忽略的 `.nexweave-data` 中；原始密钥、Cookie、数据库口令没有写入交付文件。

仓库在本轮开始前已有大量未提交修改，不能用当前 git diff 总量代表本轮变更。本轮之前的输入副本保存在 `.nexweave-data/m95-preimplementation-20260907`，用于按文件哈希比较；未 reset、提交或 push。

## 运行说明

保持既有 `.env` 本地配置。基础服务沿用 Compose；从仓库根目录执行：

```sh
docker compose up -d --build api web worker-kernel worker-parser parser-sandbox
python3.12 -m venv .nexweave-data/forecast-venv
.nexweave-data/forecast-venv/bin/pip install -r requirements/forecast.lock
.venv/bin/python scripts/fetch_m95_model.py
.nexweave-data/forecast-venv/bin/python scripts/run_m95_worker.py
```

官方站点不可达时，下载命令可显式增加 `--mirror`；只更换公开下载通道，仍校验固定权重和配置哈希。当前环境已完成安装，不需要重复下载/重建虚拟环境。Worker 使用独立终端持续运行；本轮已启动的进程 PID 保存在 `.nexweave-data/m95-worker.pid`，避免重复启动。

另一个终端执行 `.venv/bin/python scripts/verify_m95.py`，复用当前绑定并创建三个新运行；`--fresh` 明确新建演示空间。自有 CSV 先通过既有 Source 上传/解析，再调用 `POST /api/v1/spaces/{space_id}/signal-bindings`；创建预测用同空间 `/forecast-runs`，查询 `/forecast-runs/{id}` 与 `/forecast-artifacts/{id}`，具体请求以 OpenAPI 为准。

## 需求追踪与停止声明

NXW-LK-001～006 见需求矩阵：已完成“可运行技术首片”，工业数据、知识检索回接、签名 Pack 与完整 UI 深化保持 PARTIAL/OPEN。M9 原专家、真实评审和批准阈值 P0 不关闭；没有进入 M10，没有自动 commit/push，没有 GridCrew/OptiForge 执行。**停止在 M9.5 首片交付，不把后续加固事项隐含为已完成。**
