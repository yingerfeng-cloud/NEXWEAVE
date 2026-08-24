# Naming Baseline

| 对象 | 统一命名 | 约束 |
|---|---|---|
| 产品 | NEXWEAVE / NEXWEAVE 企业级 LLM Wiki 标准化平台 | UI 可展示“织界” |
| 仓库 | `nexweave` | 禁止场景名作为仓库名 |
| Python 根包 | `nexweave` | 领域包不得成为根包 |
| 前端 Scope | `@nexweave/*` | 公共 UI、contracts、sdk 统一命名 |
| 环境变量 | `NEXWEAVE_*` | 密钥只保存引用 |
| Docker 镜像 | `nexweave-web`、`nexweave-api`、`nexweave-worker-*` | 语义化版本 |
| Temporal Namespace | `nexweave-dev/test/prod` | 环境隔离 |
| Task Queue | `nexweave.compile.default`、`nexweave.review.default`、`nexweave.release.default` | 禁止客户硬编码 |
| OTel Service | `nexweave.web`、`nexweave.api`、`nexweave.worker.*` | 统一命名族 |
| Domain Pack | `<domain-id>-pack` | 首发 `equipment-rca-pack` |
| API Prefix | `/api/v1` | 禁止无版本公共接口 |
| 事件类型 | `nexweave.<domain>.<event>.v1` | 过去式业务事实，带 schema version |
| 数据库表 | `snake_case` 单数或团队统一复数策略 | M0 统一冻结，历史迁移不改名 |
| JSON 字段 | `snake_case` | OpenAPI/事件/SDK 单一语义 |
| TypeScript 类型 | `PascalCase` | 字段保持契约命名 |

## ID

公共对象使用不可预测、跨存储稳定的 ID。候选为 UUIDv7；最终方案由 M0 ADR 冻结。业务编号可作为显示字段，不能替代主 ID。

## 版本

- API、事件、Pack、Schema、Prompt、ModelProfile、Release 都显式版本化；
- Release 版本和兼容策略由 M0/M7 冻结；
- 时间统一存储为 UTC，并以 ISO 8601/RFC 3339 交换；
- 状态枚举使用稳定大写 snake case，不复用显示文案。

## 禁止词义混用

- `Source` 不等于 `Evidence`；
- `Evidence` 不等于 `Citation`；
- `Relation` 不等于 `Claim`；
- `ReviewTask` 不等于 `Approval`；
- `Release` 不等于部署环境或 Git tag；
- NEXWEAVE `Evidence` 不自动等同于 GridCrew 执行 Evidence；
- Domain Pack 不等于 GridCrew Skill。
