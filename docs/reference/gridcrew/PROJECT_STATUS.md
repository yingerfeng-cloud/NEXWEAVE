# GridCrew Project Status

Current Release: R1
Current Milestone: M-1C
M-1: Completed
M-1C: Completed
M0: Ready, Not Started
Git Baseline: Waiting for local identity

## 已冻结决策

- Temporal 是正式执行权威；PostgreSQL 保存业务事实和查询投影，不构成第二套状态机。
- Position/AccessRole、DigitalEmployee/EmployeeRelease、Artifact/Evidence 均为不同语义对象。
- Model Gateway 和 Tool Gateway 是外部调用的统一边界；Agent Runtime 不拥有企业任务生命周期。
- 统一事件 Envelope、Outbox 发布链路、幂等与审计语义已在 M-1C 冻结。

## 权威与阶段边界

用户提供的 [M0 正式任务书](docs/tasks/GridCrew_M0_终局架构冻结与工程骨架正式任务书.md) 是 M0 唯一执行依据，已原样归档且尚未执行。历史 [M0 范围摘要](docs/tasks/archive/GridCrew_M0_范围摘要_V0.1_已废止.md) 已废止。

## 待确认问题

详见 [docs/architecture/OPEN_QUESTIONS.md](docs/architecture/OPEN_QUESTIONS.md)。首批真实 Skill、Connector 和客户业务场景未被本轮决定。
