# 阶段 D 验收与可信边界运行手册

范围：11F / ADR-0036，版本 `0.9.5-d1`。不进入 M10，不改变 R1 发布权威。已有 A—C 本地合成制品是本次验证前置，不能用工业资料替换脚本中的测试对象后直接执行。

```bash
make dev-up
.venv/bin/python scripts/verify_stage_d.py
docker compose exec -T api python - 01a084fc-ba5b-7957-9e2c-8adae09555b8 < scripts/verify_stage_d_graph.py
```

HTTP 脚本读取 `.nexweave-data/stage-c-e2e.json` 与 `stage-c-reference.json`，创建合成 Query/审计记录，检查同键参数冲突、历史答案失效过滤、Graph 成员与日期门禁、知识回接和 worker 版本；不创建预测，不改历史 Source/Release。输出 `.nexweave-data/stage-d-e2e.json`。缺少 C 前置时应先按 C 手册准备隔离合成验证环境，不应伪造 ID 或结果。

数据库脚本只读已有合成答案标识，在当前会话创建临时表模拟成员/证据/源权限组合，结束显式回滚；不会修改业务表。验证 6 项 Graph 情形及 2 项多来源 Claim 密级情形。此脚本不是生产压测或迁移。

浏览器复核：

1. 进入 P-101 演示空间的 Wiki「运行与未来」，确认服务在线及数据为合成；复用已完成的 Chronos-2 记录。
2. 打开绑定向导，选择现有 CSV、已发布时序模型及 P-101，映射 timestamp/temperature/vibration/lube/load/quality 与 degC/mm/s/MPa/%；预检应通过。改变单位后保存立即禁用，再预检应提示不匹配。关闭未保存配置。
3. 选择同窗口持续工况进行对照，显示末端 P10/P50/P90 及条件预测非因果说明。
4. 选择固定发布 `7.0.1788937445`，检索 lubrication vibration，点击原文定位，看到 VALID、block/字符命中及明确合成的原文。
5. 知识图谱→发布关系图，选择上述发布与 HTTP 证据中的实体；显示 1 节点、0 关系（该合成发布未发布关系，不应造边）。切换另一个发布应清空结果；原实体非成员时拒绝。

故障诊断先查看服务健康与版本，再核对当前身份、Release 成员、Evidence/Anchor 和 Source 有效性。拒绝读取不能通过修改旧发布/解除来源失效来绕过。历史答案响应是当前授权投影；存储原文不改写。
