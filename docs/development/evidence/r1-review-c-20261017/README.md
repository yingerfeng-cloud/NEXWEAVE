# R1 Review C 批证据（执行至2026-10-18）

这是本轮新整改材料，不是历史验收追记。原DOCX/Evidence ZIP不在提交范围。

- `verification.json`：当前代码提交、执行分类、门禁/阻塞与限制；`MANIFEST.sha256`校验本目录文件。
- `quality.log`：当前make check；`database.log`：26项PG/Redis/RustFS集成。SQL夹具、替身HTTP/Temporal在测试docstring中明确，不能当工业或全业务验收。
- `r1-chain.log`、`m1.log`—`m4.log`、`m9-pack.log`：真实现有服务/声明式Pack验证；`temporal-component.log`为真实Temporal+替身Activity。
- `review-delivery-final.log`、`review-delivery-timings.json`：新个案完整5阶段真实停机恢复；`review-delivery-recovery.log`保留最初失败及恢复；`poison-update-history.json`、`review-poison-recovered.json`记录缓存失败未改写而后台重投成功。
- `migrations.log`、`migration-nonempty-guard.json`：一次性升级/回退/再升级，以及合成库克隆上的非空保护。没有删历史强制回退。
- `independent-knowledge-baseline.json`：20题真实HTTP工程基准与失效来源控制，16/20是FAIL；每题实际检索/回答/引用/拒答保留。0个虚构模型调用。
- `real-provider-baseline.json`：缺真实模型配置的显式CONFIGURATION_BLOCKED，0调用、无分数。不是模型验证通过。
- `chronos-rolling-origin.json`、`forecast-e2e.log`、`forecast-guards.log`：实际固定Chronos模型、4个时间起点及持久值基线、真实合成双场景、输入/权限/不可变约束。合成数据不是工业效果。
- `forecast-cancel-evidence.json`：真实取消运行的DB/S3/Temporal与冻结输入分别核对；模型就绪时点未关联。`chronos-rolling-origin.json`的进程取消是直接模型入口，DB/S3明确NOT_APPLICABLE。晚到PUT清理来自database.log中的真实S3组件（数值替身）。硬崩溃窗口未测试。
- `runtime-audit.json`、`node-audit.json`：当前生产锁审计；`forecast-audit.json`为可选预测严格审计FAIL。`image-gate.json`与`trivy-*.json`记录7个当前ARM64镜像ID及原有可修复HIGH/CRITICAL门槛，不替代双架构/签名/远程CI。
- `runtime-state.json`确认7个实际运行镜像与扫描ID一致；`runtime-source-check.json`核对142个当前API镜像Python文件无差异。`forecast-environment.json`及`forecast-pip-check.log`确认实际可选环境符合完整预测锁，但不能消除其中已报告的漏洞。
- `browser-state.json`和`web-*.png`：真实Web持续旅程：新空间资料/编译/审核/冲突/表单在B执行，C保留原双题完成100%、独立1.0.1发布、Query/有效原文、错误对象拒答及固定发布Graph。不是脚本预先代做。B的50%失败证据保留在B目录。

日志中的本机工作区路径和容器私网地址在复制时作展示脱敏，并移除ANSI颜色、行尾空白；没有修改状态、分数或测试断言。完整日志留在本机临时目录供核对，不含运行环境文件或凭据。

## 复跑

在仓库根使用已有配置，不覆盖用户`.env`：

```sh
COMPOSE_PROJECT_NAME=nexweave-r1-review docker compose -f compose.yaml -f docs/development/evidence/r1-review-c-20261017/compose.review.yaml up --build --detach --wait
make check PYTHON=.venv/bin/python
```

本目录override仅区分本轮镜像/开发版本；默认端口仍需空闲。使用独立Compose项目/卷，不连接生产。API启动运行新增迁移；回退限制见C报告。模型权重、虚拟环境与凭据不提交。

独立知识基准（默认词面，预期当前16/20而非通过）：

```sh
.venv/bin/python scripts/benchmark_r1_knowledge.py --output .nexweave-data/knowledge-baseline.json
```

有真实配置时使用已有Gateway环境、公开型号/revision配置模板，凭据不放配置JSON：

```sh
.venv/bin/python scripts/benchmark_r1_models.py --config tests/benchmarks/model-profiles.example.json --check-config --output .nexweave-data/model-baseline.json
```

先填实际型号/revision等公开配置，确认后去掉`--check-config`执行真实文本和embedding。空模板/缺key/缺HTTPS网关明确失败，不能计分。该runner只允许loopback开发环境和合成技术身份。

固定Chronos本地回测：

```sh
PYTHONPATH=apps/api/src:packages/contracts/src:packages/domain/src:packages/application/src .nexweave-data/forecast-venv/bin/python scripts/benchmark_forecast.py --output .nexweave-data/chronos-backtest.json --cancel-check
```

可传`--csv`、`--unit`、`--history`、`--horizon`、`--origins`、`--step`与`--train-fraction`；固定revision/权重仍检查。真实领域数据需自行准入和独立验收；未提供时不伪造。
