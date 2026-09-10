# NEXWEAVE M4 本地运行手册

## 1. 启动与健康

```bash
make dev-up
docker compose ps
```

API `GET /api/v1/version` 应返回 milestone `M4`，数据库 revision 应为 `0005_m4`。本地 development 环境使用已有 dev identity；非 development 环境必须使用 OIDC 和外部 Secret Provider。

## 2. 标准操作顺序

1. 平台管理员通过 `POST /api/v1/domain-pack-trust-keys` 登记 Ed25519 公钥及其 namespace；私钥永不进入 NEXWEAVE。
2. 治理管理员通过 `POST /api/v1/domain-packs` 提交 canonical manifest 与声明内容。服务端先验证 path、checksum、namespace ownership、签名、资源预算和撤销状态。
3. 知识工程师创建 SchemaDefinition，或选择已有 Schema 版本链。
4. 通过 `POST /api/v1/spaces/{space_id}/domain-pack-installations` 启动 Pack 安装；响应的 Installation/Workflow/Run ID 是恢复和审计依据。
5. 安装成功只生成 DRAFT SchemaVersion。调用 validate 查看 compatibility、impact 和 migration preview；授权 publisher 使用强 ETag 和幂等键独立 publish。
6. 升级创建新安装和候选版本；disable 重新组合且保留历史；rollback 恢复精确历史候选，不修改旧 Schema/Pack/report。
7. 受信任平台根可导入离线签名 revocation list。撤销阻断后续安装/列表，不删除历史事实。

Schema Studio 和 Pack Center 都只调用上述公共 API；刷新后使用服务器状态和已保存的 Installation ID 恢复，不在浏览器维护第二状态机。

## 3. 验证

```bash
make check PYTHON=.venv/bin/python
make migration-check
make verify-m4 PYTHON=.venv/bin/python
```

`verify-m4` 可重复执行：失败路径与撤销路径均创建本次运行独立的签名 fixture；撤销只作用于隔离目标，不改变后续验收所需的可安装 Pack。

Workflow v1/v2 compatibility against the running local Temporal:

```bash
NEXWEAVE_TEMPORAL_TEST_ENDPOINT=127.0.0.1:7233 \
NEXWEAVE_TEMPORAL_TEST_NAMESPACE=nexweave-dev \
.venv/bin/pytest -q workers/kernel/tests/test_m4_pack_workflow.py -m integration
```

完整回归使用 `make verify`，依次验证 M1—M4；M0 可单独运行 `make verify-m0`。

## 4. 常见诊断

- `PACK_SIGNATURE_INVALID`：确认签名 descriptor 排除了 `security.signature.value`，其余字段使用 JSON canonical 值；UTC datetime 必须在签名前规范化。
- `PACK_REVOKED`：检查 exact content checksum 或 signing key 是否在已签名撤销清单中。不得删除撤销记录或历史安装绕过。
- `PACK_DEPENDENCY_CONFLICT`：确认依赖 Pack 已注册、版本范围唯一解析且未撤销；依赖循环不能靠安装顺序解决。
- `PACK_COMPOSITION_CONFLICT`：检查重复 stable key 的 canonical 定义、DAG、继承、端点和 EXACT mapping；禁止最后写入获胜。
- `SCHEMA_BREAKING_CHANGE`：读取 CompositionReport 和 preview-only migration operations，创建显式下一版草稿；不得修改已发布版本。
- Installation 长时间 `INSTALLING`：使用 Workflow ID/Run ID 检查 Temporal 和 worker-kernel，并对照审计/WorkflowTask 投影；不要直接改数据库终态。

## 5. 安全与停止边界

- Pack 仅允许 JSON 声明，不接受脚本、宏、二进制、远程 include、自定义组件或动态表达式。
- Fixture 私钥仅用于测试，不得用于生产信任根。
- M4 migration DSL 只预览，不执行实例变换。
- M4 完成后不得启动 Compile、Review、Release、Query、GridCrew 或 RCA 实施；必须等待 M5 明确下发。
