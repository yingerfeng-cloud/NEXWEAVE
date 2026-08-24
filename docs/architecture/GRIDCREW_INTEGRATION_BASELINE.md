# GridCrew Integration Baseline

> 状态：M-1 联合契约草案。首期为固定 Release 的只读知识消费；两产品独立部署、独立数据库、独立生命周期。

## 1. 产品边界

```text
GridCrew: DigitalEmployee / EmployeeRelease / Task / Skill / Tool / Artifact / Execution Evidence
NEXWEAVE: Source / Schema / Wiki / Claim / Knowledge Evidence / Review / Evaluation / Release
```

GridCrew 负责任务编排与执行；NEXWEAVE 负责可信知识生产与发布。NEXWEAVE 不接管 GridCrew Task 生命周期，GridCrew 不接管 NEXWEAVE Review/Release 生命周期。

## 2. GridCrew → NEXWEAVE

| 能力 | R1 范围 | 边界 |
|---|---|---|
| Knowledge Query | 固定 `space_id + release_id` 的带引用查询 | 禁止默认草稿和跨 Release 混用 |
| Evidence Read | 按 Citation 读取有权限的 Evidence 元数据/片段 | 不绕过 Source 密级和下载策略 |
| Graph Traverse | 固定 Release 的关系遍历 | Relation 必须带 Evidence 状态 |
| Release Metadata | 版本、manifest hash、状态、兼容/废止信息 | 不返回内部草稿配置 |
| Compile Submission | 后续可提交受控编译任务 | R1 M8 可先保留契约；只生成草稿 |
| Feedback/Case Draft | 任务反馈、案例草稿、冲突线索 | 进入 Feedback Workflow，不直接发布 |

## 3. NEXWEAVE → GridCrew

| 事件/通知 | 用途 |
|---|---|
| Release Published | Skill/EmployeeRelease 可选择升级绑定版本 |
| Release Pointer Changed | 订阅默认通道的消费者获知切换；运行中 Task 仍锁定原版本 |
| Release Deprecated | 提示替代版本和有效期，不静默改运行中 Task |
| Domain Pack Updated | 提示 Knowledge Pack/Skill 兼容评审 |
| Review/Conflict Notification | 仅当 GridCrew 承载通知/待办入口；权威审核仍在 NEXWEAVE |
| Feedback Receipt | 回执已进入哪个草稿/审核入口及 correlation ID |

## 4. Knowledge Pack → Skill 映射

GridCrew Skill Version 中保存引用，而不是复制 NEXWEAVE 内核：

```json
{
  "provider": "nexweave",
  "tenant_mapping_id": "mapping-id",
  "space_id": "space-id",
  "release_id": "release-id",
  "domain_pack_id": "equipment-rca-pack",
  "domain_pack_version": "1.0.0",
  "query_policy_version": "policy-id",
  "allowed_operations": ["query", "evidence.read", "graph.traverse"]
}
```

GridCrew `EmployeeRelease`/Task 必须锁定 Skill Version，从而间接锁定 NEXWEAVE Release。新知识发布不静默改变运行中任务。

## 5. 共享与不共享

| 主题 | 原则 |
|---|---|
| Tenant/User | 可通过 OIDC subject 和映射表关联，不共享业务主键或数据库 |
| Service Identity | 双方独立注册、受众、最小权限和轮换；可建立受信服务调用 |
| Model Gateway | 可兼容或复用服务，但调用记录、数据分类和可用性边界需 ADR |
| Connector | 共享 SPI 原则，不共享实例状态/凭据；GridCrew 外部动作仍经 Tool Gateway |
| Evidence | NEXWEAVE Knowledge Evidence 与 GridCrew Execution Evidence 语义分离，可交叉引用 |
| Approval | 双方各自保存本产品业务批准；跨平台只传签名决策引用/回执 |
| Artifact | NEXWEAVE Release/导出包可成为 GridCrew Artifact 引用，但对象不合并 |
| Workflow | 独立 Temporal Namespace/Workflow；不跨产品共享 Workflow 状态 |

## 6. 身份、租户、权限与审计

- 服务令牌必须限制 issuer、audience、tenant mapping、space、release 和 operation；
- 用户委托查询需保留原用户 subject、服务身份和授权链；
- NEXWEAVE 服务端重新授权，不能信任 GridCrew UI 或请求中的任意 scope；
- correlation ID 贯穿 GridCrew Task/Skill Run、API、NEXWEAVE Query 和 Model Call；
- 两边分别写不可变审计，并保存对方 request ID/receipt ID；
- 高密资料的 Evidence 内容可拒绝返回，只返回允许的元数据或脱敏片段。

## 7. 幂等、重试与错误

- GridCrew 请求包含稳定 `operation_id/request_id`；同 ID 同负载返回同一结果，同 ID 异负载返回 409；
- Query 可同步返回或异步返回 answer ID，超时不意味着业务失败；
- Webhook 至少一次投递，使用 delivery ID、签名、时间戳和重放窗口；
- 错误区分认证、授权、版本不存在/废止、Evidence 不可见、证据不足、Provider 暂不可用和速率限制；
- 5xx/网络超时可按退避重试；4xx 业务错误默认不可重试。

## 8. 阶段策略

- R1/M8：只读固定 Release 查询、Evidence、Graph、Release metadata 和发布事件；反馈只能进入草稿入口。
- R3/M14：在双方治理、审批和回执语义稳定后扩展双向知识回流与多应用闭环。

## 9. 联合依赖

GridCrew 当前 M0 尚未开始。NEXWEAVE M8 前，GridCrew 至少需要可用的 ServiceIdentity、Skill Version、EmployeeRelease 固定资产引用、Tool/Connector 调用治理、Artifact/Evidence 引用、事件 Envelope 和审计链。双方须在各自编码前共同冻结 OpenAPI、事件 Schema、租户映射、错误码和测试 fixture。
