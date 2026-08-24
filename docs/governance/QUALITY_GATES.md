# Quality Gates

## 1. 文档门禁

- 当前 Milestone、上阶段报告、Accepted ADR、Open Questions 和需求追踪一致；
- 公共对象、状态、版本、权限、错误、API、事件、Workflow 和迁移文档同步；
- 用户/管理员/开发者文档反映真实功能，不含伪造结果；
- 依赖、许可证、安全影响、数据迁移和回滚说明齐全。

## 2. 架构门禁

- `domain`/`contracts` 不依赖 FastAPI、SQLAlchemy、Temporal、存储或厂商 SDK；
- Workflow 确定性，外部操作仅 Activity/Task；
- Adapter/Provider 通过公共 Port，业务代码不绑定 SQLite/PostgreSQL/RustFS/模型厂商；
- Domain Pack 不依赖平台内部实现、不执行任意代码；
- GridCrew 集成位于 Integration/SDK 层，不侵入核心；
- Search/Vector/Graph 可由固定 Release 重建。

## 3. 契约门禁

- OpenAPI、事件、SDK、Pack manifest、Provider 和 GridCrew 契约通过自动化检查；
- 所有写接口定义权限、幂等、乐观锁、审计和稳定错误码；
- 破坏性变化有 ADR、版本升级、兼容窗口和迁移计划；
- Release/Evidence/SourceAnchor 变化必须专项评审。

## 4. 安全门禁

- Secret scan、SCA、SBOM、许可证和高危漏洞检查通过；
- 跨租户/空间/对象越权、草稿泄漏、密级、职责分离和审计测试通过；
- 文件/Parser、Prompt 注入、SSRF、Webhook、Pack 供应链测试通过；
- 无明文凭据、内部地址、真实敏感资料或未脱敏日志。

## 5. 代码门禁

- format、lint、typecheck、unit、contract、migration、frontend build 全部通过；
- 核心代码有类型、错误处理、审计、可观测性和自动化测试；
- 无静态 UI/Mock/固定 JSON 冒充真实完成；
- 新依赖用途、版本、许可证、风险和替代方案已记录。

## 6. 测试门禁

- 单元：领域规则、状态机、权限、幂等、转换、Provider；
- 架构：依赖方向、厂商隔离、Workflow 确定性；
- 契约：OpenAPI、事件、SDK、Pack、GridCrew；
- 集成：真实 PostgreSQL、RustFS、Temporal、Redis 和相关 Provider；
- Workflow：Replay、时间跳跃、重试、取消、补偿、Worker 恢复、投影对账；
- E2E：Source→Compile→Review→Evaluate→Release→Query；
- 安全/故障/恢复：按当前 Milestone 风险执行；
- 测试结果、命令、环境、数据版本和未执行项如实记录。

## 7. 知识质量门禁

- 正式 Claim 与因果 Relation 有有效 Evidence；
- Evidence 可定位到固定 SourceVersion 原文；
- 阻断 Conflict 关闭或经明确策略处置；
- 发布知识来源可追溯率与 Schema 合规率 100%；
- Release 固定 Schema、Prompt、Model、对象版本和索引配置；
- Query 固定 Release、记录 Citation；证据不足明确拒答/不确定；
- 引用准确率、问题覆盖率和专家接受率达到经批准的试点阈值。

## 8. 发布门禁

- ReleaseCandidate 的依赖、权限、Evidence、冲突、Lint、评测和 Approval 全部通过；
- Release manifest 不可变且可签名/校验；
- 索引构建验证成功后才切换指针；
- 回滚不修改历史，发布/回滚/废止事件和审计一致；
- 固定 Release 的回答和引用可复现。

## 9. 阶段门禁

- M-1 未验收不得进入 M0；
- M0 未冻结核心对象、状态、版本、API、事件、Workflow、权限、错误和迁移策略不得进入 M1；
- 每个 Milestone 未通过不得自行进入下一阶段；
- P0 架构、权限、Evidence、Release 或安全缺口不能以“后补”关闭。

## 10. M-1 门禁结果要求

M-1 只验收资料、治理、基线、契约草案、追踪、ADR/Spike 和开放问题；不得以任何业务功能或原型交互作为完成证据。
