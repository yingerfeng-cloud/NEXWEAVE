# GridCrew 统一事件目录

本文定义 M-1C 事件语义，不实现消息总线、Outbox 或消费者。

## Event Envelope

所有内部事件必须包含以下字段：

```text
event_id
event_type
schema_version
tenant_id
organization_id
workspace_id
actor_id
actor_type
occurred_at
correlation_id
causation_id
trace_id
idempotency_key
payload
```

- `event_id` 是消息级唯一标识，用于投递去重。
- `schema_version` 是事件契约版本。
- `correlation_id` 关联同一业务链路；`causation_id` 指向直接触发本事件的命令或上游事件。
- `trace_id` 是可观测链路标识。
- `idempotency_key` 是业务操作幂等键，不等同于 `event_id`。

## 生产与发布边界

业务语义生产者决定事件内容；技术发布者负责将 Outbox 中已提交的事件发送至消息基础设施。标准发布链路是：

```text
Temporal Workflow -> purpose-specific Activity -> business projection or Outbox -> Event Publisher -> consumer
```

Workflow 代码不得直接访问数据库、HTTP 或消息总线。Activity 负责确定用途的 I/O；业务投影或 Outbox 的写入必须可审计。

## 幂等语义

不得以 `tenant_id:task_id:step:status`、`tenant_id:approval_id:decision` 或 `tenant_id:task_id:failed` 作为唯一业务幂等依据。

不得以 `tenant_id:approval_id:decision` 作为唯一业务幂等依据。

| 场景 | 幂等或排序依据 |
|---|---|
| 事件投递 | `event_id` |
| 有序状态变化 | 对象 `version` 或 `sequence` |
| 外部副作用 | 稳定 `operation_id` |
| 审批轮次 | `approval_round` |
| Workflow 命令 | `command_id` |
| Tool 调用 | `tool_call_id` 与外部幂等键 |

相同状态可在不同轮次发生；状态文本本身不是唯一幂等键。
