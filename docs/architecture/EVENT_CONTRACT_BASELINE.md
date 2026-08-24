# Event Contract Baseline

> M0 已冻结 envelope、版本与幂等语义；事件目录由后续业务 Milestone 实现。M0 只创建 transactional outbox 基础表，不运行 Broker。

## 1. Envelope

```json
{
  "specversion": "1.0",
  "id": "uuid-v7",
  "type": "io.nexweave.release.published.v1",
  "source": "/nexweave/release",
  "subject": "release/{release_id}",
  "time": "2026-08-23T00:00:00Z",
  "datacontenttype": "application/json",
  "dataschema": "https://contracts.nexweave.local/events/release-published/v1",
  "tenant_id": "uuid-v7",
  "space_id": "uuid-v7",
  "aggregate_id": "uuid-v7",
  "aggregate_version": 1,
  "correlation_id": "uuid-v7",
  "causation_id": "uuid-v7",
  "trace_id": "opaque-trace-id",
  "classification": "INTERNAL",
  "data": {}
}
```

- 事件是已发生业务事实，禁止用事件伪装命令。
- 业务事务通过 Outbox 原子记录；发布至少一次，消费者必须幂等。
- Payload 只包含最小必要信息，Raw 内容、凭据和高密原文不进入普通事件。
- 破坏性变化发布新 major event type；旧消费者保留兼容窗口。

## 2. 初始事件目录

| 事件 | 生产者 | 主要消费者 | 最小 Payload | 阶段 |
|---|---|---|---|---|
| `io.nexweave.space.created.v1` | Workspace | Audit/Admin | space id/status | M1 |
| `io.nexweave.membership.changed.v1` | IAM | Audit | subject, policy version, action | M1 |
| `io.nexweave.source.version-ready.v1` | Source | Parse Workflow | source/version/checksum/classification | M3 |
| `io.nexweave.source.invalidated.v1` | Source | Evidence/Release/Index | source version, reason | M3 |
| `io.nexweave.parse.completed.v1` | Parse Workflow | Compile/UI | parse job, source version, result version | M3 |
| `io.nexweave.parse.failed.v1` | Parse Workflow | UI/Alert | job, stable error, retryable | M3 |
| `io.nexweave.schema.published.v1` | Schema | Compile/Pack/UI | schema/version/compatibility | M4 |
| `io.nexweave.pack.installed.v1` | Pack Workflow | Schema/Audit | pack version, installation, space | M4 |
| `io.nexweave.compile.completed.v1` | Compile Workflow | Review/Quality/UI | job, output versions, stats | M5 |
| `io.nexweave.conflict.detected.v1` | Compile/Conflict | Review/Notification | conflict, severity, affected refs | M5/M6 |
| `io.nexweave.review.requested.v1` | Review Workflow | Notification/UI | task, assignee policy, due time | M6 |
| `io.nexweave.review.completed.v1` | Review Workflow | Quality/Release | task, decision, approved versions | M6 |
| `io.nexweave.evaluation.completed.v1` | Evaluation Workflow | Release/UI | run, target, gate summary | M7 |
| `io.nexweave.release.published.v1` | Release Workflow | Query/Index/GridCrew | release, space, manifest hash, policy | M7/M8 |
| `io.nexweave.release.pointer-changed.v1` | Release | Query/GridCrew | channel, old/new release, reason | M7/M8 |
| `io.nexweave.release.deprecated.v1` | Release | GridCrew/subscribers | release, effective time, replacement | M7/M8 |
| `io.nexweave.connector.sync-completed.v1` | Connector Workflow | Source/UI | run, watermark, source versions | M8 |
| `io.nexweave.gridcrew.feedback-accepted.v1` | Feedback Workflow | GridCrew/Review | external id, intake id, draft status | M8 |

## 3. 幂等与审计

生产端以业务事务 + Outbox 防止“业务成功但事件丢失”；发布端按 event ID 重试；消费端保存 consumer/event ID 或等价幂等事实。所有外部 Webhook 使用签名、时间戳、重放窗口和 delivery ID，并将最终状态写入双平台审计。

事件 JSON Schema 位于 `packages/contracts/schemas/event-envelope.schema.json`。Broker、保留周期、重放、死信、顺序、分区键与 GridCrew 字段映射在首次引入 Broker/M8 集成前冻结；M0 不虚构具体中间件能力。
