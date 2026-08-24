# GridCrew 术语表

| 术语 | 含义 | 禁止混用 |
|---|---|---|
| PositionTemplate | 可复用岗位模板。 | 不等同于 AccessRole。 |
| Position | 租户组织内实际岗位。 | 不等同于 RBAC 权限角色。 |
| AccessRole | RBAC 权限角色。 | 不得称为岗位或 `Role`。 |
| PermissionPolicy | ABAC、数据范围和风险条件策略。 | 不等同于 AccessRole 或 Position。 |
| DigitalEmployee | 稳定数字员工身份。 | 不携带可变发布版本作为主身份。 |
| EmployeeRelease | 不可变的数字员工可执行发布快照。 | 不等同于 DigitalEmployee。 |
| Task | 业务任务事实及其业务状态投影。 | 不等同于 Temporal Workflow。 |
| WorkflowExecutionReference | Task 到 Temporal 执行的引用。 | 不创建第二套执行状态机。 |
| Artifact | 交付成果或大型中间产物。 | 不等同于 Evidence。 |
| Evidence | 事实、来源或执行真实性证据。 | 不由模型生成文本替代。 |
| Event Envelope | 内部事件的统一契约外壳。 | `event_id` 不等同于 `idempotency_key`。 |
| Outbox | 与业务投影一致写入、待技术发布者发送的事件记录。 | 不允许 Workflow 直接访问消息总线。 |
| Model Gateway | 所有模型调用的统一治理入口。 | 不等同于业务模型供应商。 |
| Tool Gateway | 所有外部工具和系统调用的统一治理入口。 | 不等同于 Connector。 |
