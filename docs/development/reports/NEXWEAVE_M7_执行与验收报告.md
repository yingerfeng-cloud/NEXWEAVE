# NEXWEAVE M7 执行与验收报告

## 1. 结论

用户于 2026-08-31 正式下发并正式验收 M7。ADR-0026、实现、迁移、自动化回归和隔离真实端到端验收已完成；该验收不授权进入 M8。

## 2. 完成范围

- 质量中心：版本化 EvaluationSuite/Case/Run/Result、逐题错误、检索配置与发布门禁。
- 发布管理：显式 ReleaseCandidate items、Lint/Evaluation/Conflict/Evidence gates、独立 Publisher、不可变 Release/Items、历史、废止、JSON/Markdown 导出、投影重建和指针回滚。
- 检索与图谱：Search/Vector/Graph ports，PostgreSQL FTS + pgvector + Relation，RRF、密级过滤、1—5 跳/最短/因果/时间切片。
- 可信问答：固定单一 Release、QuerySession/Answer/Citation、客户端请求幂等、Evidence/VALID Anchor 校验、不确定性/冲突返回和证据不足拒答。
- 前端与 SDK：真实 API 驱动的 Quality、Release、Graph、Ask 页面，Python/TypeScript SDK 与 OpenAPI/JSON Schema 同步。

## 3. 架构、数据与 Workflow

- ADR-0026 冻结 Release/Query/Projection 语义。
- additive `0008_m7_quality_release_query` 不修改 `0001`—`0007`，增加 M7 事实表、复合租户/空间约束、pgvector/FTS 索引和不可变触发器。
- `nexweave.quality-evaluation.v2` 与 `nexweave.knowledge-release.v2` 只编排固定引用；数据库、模型和投影 I/O 位于可重试 Activity。
- 事件：`evaluation.completed.v1`、`release.published.v1`、`release.pointer-changed.v1`、`release.deprecated.v1` 通过业务事务 Outbox 记录。

## 4. 发布、回滚与回答复现证据

隔离验收从已接受的 M6 Claim/Evidence 数据只读复制开始，使用独立临时 PostgreSQL 数据库和专用 Temporal Workflow/Activity 队列：

1. 创建固定 Schema 的两题 EvaluationSuite（可回答 + 证据不足）。
2. 创建并验证两个不同 SemVer ReleaseCandidate；两者均达到来源追溯 100%、Schema 合规 100%、Evaluation 通过且无阻断项。
3. 由与创建者不同的 Publisher 批准，得到两个不可变 Release。
4. 对第一个固定 Release 重复同一 client request，返回同一 QueryAnswer 和 Evidence/SourceVersion/SourceAnchor 引用。
5. 无关问题返回 `REFUSED` 且 Citation 为空。
6. JSON export 包含 manifest checksum 和固定 Items；projection rebuild 后 checksum 不变。
7. 以强 ETag 将 stable pointer 从新 Release 回切旧 Release；Pointer version 只增 1，两个历史 Release 均未修改。

最终输出：`M7 real chain verified: ... two immutable Releases ... reproducible query, refusal, export, projection rebuild and pointer-only rollback.` 临时数据库与 dump 已删除，共享 M6 空间和指针未改动。

## 5. 验证结果

- Ruff：通过。
- strict mypy：通过。
- Python：112 passed（含真实本地 Temporal），此前非集成集为 107 passed、5 deselected。
- Web：15 tests、lint、typecheck 与 production build 通过。
- 迁移：真实 PostgreSQL `M0→M7→M6→M7` 通过，M7 tables、pgvector projection 与 M0—M4 sentinel data 保持。
- M7 隔离真实 E2E：通过。
- OpenAPI/JSON Schema：已生成并进入防漂移检查。

最终收尾已复跑上述全量门禁；API/Worker/Web 最终镜像重建成功，全部定义 healthcheck 的本地 Compose 服务为 healthy。远程 CI 未运行，因为没有 commit/push 授权。

## 6. 安全、证据与审计

- 默认拒绝 RBAC+ABAC 与密级过滤在服务端执行；前端不授予权限。
- Release 仅接受正式 Approved Claim/Relation 和 accepted Evidence + VALID Anchor；草稿无查询路由。
- 创建者/Publisher 职责分离；审批、发布、指针、废止、重建和查询均审计。
- Release、ReleaseItem、评测结果、指针历史、Citation 等关键事实由数据库不可变保护。
- 未新增依赖或凭据；无客户、设备或 RCA 专用分支；Model Gateway 未绕过。

## 7. 风险与遗留

- P1：远程 CI、双架构镜像/SBOM/CVE/Cosign 未在本轮运行；生产 OIDC/Secret Provider、外部模型 adapter 与规模性能未验证。
- P2：真实 RCA 评测集、引用准确率/覆盖率/专家接受率阈值仍待 M9 专家材料；专门发布崩溃窗口和 HA/DR 演练待部署/M12。
- 本地 deterministic embedding 仅为可回放验收 Provider，不代表外部模型效果。

## 8. 需求追踪与停止声明

RTM 中 M7 Quality/Release/Graph/Query、固定 Release 可追溯、投影重建和 100% 门禁更新为 `VERIFIED（M7 USER ACCEPTED）`，保留后续试点/生产证据边界。

当前停止在已验收 M7；未进入 M8，未实现 Connector/GridCrew 集成，未提交或推送 Git。
