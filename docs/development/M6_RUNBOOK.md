# NEXWEAVE M6 Runbook

## 本地验证顺序

1. 启动并重建本地运行时：`docker compose up -d --build api worker-kernel web`。
2. 确认数据库已到 `0007_m6`：`docker compose exec -T api alembic current`。
3. 运行静态、类型和回归：`ruff check .`、`mypy`、`pytest -q`，以及 Web format/lint/typecheck/test/build。
4. 运行 `python scripts/check_migrations.py`；它在一次性数据库中验证 `0001→0007→0005→0007`，并检查 M0—M5 保留与 M6 残留清理。
5. 先运行 `python scripts/verify_m5.py` 生成无敏感合成的 Source/Schema/Compile 候选，再将输出的 space/candidate ID 传给 `python scripts/verify_m6.py`。

## M6 真实验收链路

- 空间管理员创建 HIGH 策略：ENGINEERING → EXPERT → APPROVAL。
- 三个不同的合成身份分别执行初审、专家复核和终审。
- 终审前服务端验证候选具有至少一条 `VALID` SourceAnchor Evidence；通过后创建正式 Claim 与追加式 Evidence 记录。
- 冲突检测把 M5 ConflictCandidate 显式聚类为 ConflictCase；决策保存双方对象/证据快照和理由。
- `nexweave.human-review.v2` 只等待最终经审计的决定；v1 保持历史 Kernel Stub。

## 安全检查

- 权限在 API 端按 tenant、space、role、clearance 校验；前端仅呈现 API 返回。
- 高风险创建人及先前审核人不能担任最终批准人。
- Evidence 与 ReviewAction、ConflictDecision 均为不可修改/删除的追加事实。
- 该验证只创建合成数据，不调用外部模型或 Connector。
