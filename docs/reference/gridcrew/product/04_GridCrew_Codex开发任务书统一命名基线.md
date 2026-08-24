# GridCrew Codex开发任务书统一命名基线

后续正式Codex任务书必须以GridCrew V2.2 PRD、高保真原型V2.2和开发计划V2.2为唯一上位基线。

## 任务书命名

- GridCrew R1开发任务总纲
- GridCrew M0：终局架构冻结与工程骨架
- GridCrew M1：平台基础与核心领域模型
- GridCrew M2：Temporal可靠执行内核
- GridCrew M3：数字员工装配、Agent Runtime与能力体系
- GridCrew M4：协作空间与正式任务闭环
- GridCrew M5：首批场景、Skill与Connector
- GridCrew M6：生产治理、安全与可观测性
- GridCrew M7：真实E2E、故障演练与联合试点验收

## 工程命名

- Git仓库：`gridcrew`
- Python根包：`gridcrew`
- 前端包scope：`@gridcrew/*`
- 环境变量：`GRIDCREW_*`
- Docker镜像：`gridcrew-web`、`gridcrew-api`、`gridcrew-worker-*`
- Temporal Namespace：`gridcrew-dev`、`gridcrew-test`、`gridcrew-prod`
- Temporal Task Queue：`gridcrew.agent.default`、`gridcrew.tool.default`、`gridcrew.artifact.default`
- OpenTelemetry Service：`gridcrew.web`、`gridcrew.api`、`gridcrew.worker.*`

## 使用约束

旧版《Codex第一阶段产品需求与开发任务书》基于早期架构，不得仅替换名称后继续使用。正式R1任务书应依据V2.2架构重新编写，确保Temporal-first、统一领域对象、Skill/Tool/Connector解耦、多租户、权限、证据、审计和版本体系全部成立。
