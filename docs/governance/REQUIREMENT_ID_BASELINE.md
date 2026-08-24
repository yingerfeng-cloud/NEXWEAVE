# Requirement ID Baseline

格式：`NXW-<DOMAIN>-<NNN>`，编号一经进入 Accepted/Implemented 不复用。

| Domain | 含义 |
|---|---|
| DASH | 总览 |
| SPACE | 知识空间 |
| SOURCE | 资料与解析 |
| COMPILE | 编译与任务 |
| WIKI | Wiki |
| SCHEMA | Schema Studio |
| CLAIM | Claim/Evidence |
| GRAPH | 关系图谱 |
| CONFLICT | 冲突 |
| REVIEW | 审核/批准 |
| QUALITY | Lint/评测 |
| RELEASE | 正式发布 |
| QUERY | 查询/问答 |
| PACK | Domain Pack |
| INTEGRATION | Connector/GridCrew/Obsidian |
| ADMIN | 身份、配置、审计 |
| NFR-PERF | 性能 |
| NFR-AVL | 可用性/恢复 |
| NFR-SEC | 安全 |
| NFR-AUD | 可解释/审计 |
| NFR-COMPAT | 兼容性 |
| ARCH | 架构约束 |

## 状态

- `BASELINED`：已从上位资料提炼，尚未实现；
- `APPROVED`：产品/架构负责人批准进入当前 Milestone；
- `IN_PROGRESS`：已纳入实施；
- `IMPLEMENTED`：代码完成但门禁未全部通过；
- `VERIFIED`：验收证据通过；
- `DEFERRED`：有批准记录的延期；
- `REJECTED`：明确不建设并保留理由。

每条需求必须链接上位来源、原型、Milestone、核心对象、API/事件/Workflow、测试和验收证据。变更语义时新增版本记录，不直接重写历史验收结论。
