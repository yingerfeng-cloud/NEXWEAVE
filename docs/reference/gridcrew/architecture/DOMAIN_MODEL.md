# GridCrew 领域模型基线

本文定义一线领域语义，不生成 ORM、迁移或业务代码。所有租户内对象均带有 `tenant_id`，并按需要关联 `organization_id` 和 `workspace_id`。

| 对象 | 定义与权威 | 关键标识 | 版本和关系 |
|---|---|---|---|
| PositionTemplate | 平台或租户可复用的岗位模板；不是权限角色。 | `position_template_id` | 可版本化；可实例化为 Position。 |
| Position | 租户组织内的实际岗位，承载组织职责与人员/员工编制。 | `position_id` | 引用 PositionTemplate；不授予 RBAC 权限。 |
| AccessRole | RBAC 权限角色；只表达权限集合。 | `access_role_id` | 可绑定人类、服务或数字员工身份；不得表达岗位。 |
| PermissionPolicy | ABAC 条件、数据范围和风险规则。 | `policy_id`, `version` | 与 AccessRole 组合执行；不替代 RBAC。 |
| DigitalEmployee | 稳定的数字员工身份。 | `employee_id` | 不以可变版本为主身份；关联 Position 与已发布 EmployeeRelease。 |
| EmployeeRelease | 不可变、可执行的数字员工发布快照。 | `employee_release_id` | 固化岗位、Skill、模型、知识、工具、记忆和权限引用；Task 必须锁定它。 |
| Task | PostgreSQL 中的业务事实和用户可见业务状态投影。 | `task_id`, `version` | 记录标题、目标、发起人、参与者和 Artifact 引用；不自行推进执行状态机。 |
| WorkflowExecutionReference | 指向 Temporal 执行的引用。 | `workflow_id`, `run_id` | 同时保存 Namespace、Workflow Type 和 Task Queue；Temporal 是执行权威。 |
| Artifact | 正式交付成果或大型中间产物。 | `artifact_id`, `version` | 可关联多个 Evidence；可版本化、归档与引用。 |
| Evidence | 支持事实、来源和执行真实性的证据。 | `evidence_id`, `checksum` | 保存 source、request_id、service/model version 与 data_time；不能由模型生成文本替代。 |
| ToolCall | 受 Tool Gateway 管理的外部调用事实。 | `tool_call_id`, `operation_id` | 保存外部幂等键、审计和 Evidence 引用。 |

## 权威边界

- PostgreSQL 保存 Task 的业务事实、业务状态投影、版本和查询所需数据。
- Temporal 保存 Workflow 生命周期、等待、重试、恢复、取消和补偿。PostgreSQL 的执行状态仅是 Temporal 投影。
- Task 与 Temporal 的关联必须由 `WorkflowExecutionReference` 表达；Task 不得形成可独立推进的第二套状态机。
- DigitalEmployee 升级只能创建新的 EmployeeRelease，绝不静默改变运行中 Task 锁定的 `employee_release_id`。
- `Role` 不再作为领域对象名称。岗位使用 PositionTemplate/Position，权限使用 AccessRole。

## 关联约束

1. 一个 Artifact 可关联零个或多个 Evidence；Evidence 可支持多个 Artifact、Task 或 Audit Event。
2. Evidence 至少保留 `checksum`、`source`、`request_id`、`service_or_model_version` 和 `data_time`。
3. 人类、数字员工、服务身份和外部系统身份分别映射到 IAM 主体；它们通过 AccessRole 和 PermissionPolicy 获得授权。
4. Skill、Workflow、Tool、Connector、Model Policy 和 EmployeeRelease 都是版本化资产；M0 只建立工程骨架，不实现这些业务对象。
