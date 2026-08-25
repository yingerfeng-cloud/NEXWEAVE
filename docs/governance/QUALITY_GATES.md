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

## 11. M1 本地门禁证据（2026-08-24）

- `make check PYTHON=.venv/bin/python`：format、lint、mypy、Web typecheck、Python 28 项非集成测试、Web 5 项测试、契约 14 项、SDK check、生产 Web build 全部通过；
- `.venv/bin/python scripts/verify_m1.py`：最终镜像与迁移恢复后均通过真实 Web/OIDC-local/API/PostgreSQL/RustFS/Temporal Worker E2E；
- `docker compose exec -T api python scripts/check_migrations.py`：真实 PostgreSQL `base → head → base → head` 通过；
- Secret scan、`pip check`、Python/JavaScript 生产依赖 audit、Compose config 和 `git diff --check` 通过；
- Temporal SDK 的独立 time-skipping 临时测试服务因官方下载持续无响应，在 90 秒后人工中止；真实 Compose Temporal health Workflow 已两次通过，故不以该下载项冒充成功，也不构成 M1 业务 Workflow 缺口。

本节前述条目记录 M1 验收时的本地合成环境证据。2026-08-25 用户随后明确授权提交并 push；合并 M1/M2 交付的功能门禁提交 `ddbcc6e` 已由 GitHub Actions run `32808198635` 验证，外部 CI 与双架构镜像 SBOM/CVE/Cosign 回执已取得。生产 OIDC/Secret Provider 仍须目标环境联调。

## 12. M2 门禁证据（2026-08-24—2026-08-25）

- `make check PYTHON=.venv/bin/python`：format、Ruff、mypy（48 source files）、ESLint、TypeScript、Prettier、SDK 与 production build 通过；Python 39 passed/2 integration deselected，契约子集 17 passed，Web 6 passed；
- `.venv/bin/python scripts/verify_m2.py`：真实 Temporal 七类 Workflow、首次瞬态 Activity 重试、重复 Update、批准、暂停/继续、取消/补偿、投影损坏/修复、Worker 停止/恢复和历史 Replay；
- 隔离真实 PostgreSQL 数据库完成 `base → head → base → head` 并回到 `0003_m2`，随后仅删除该一次性数据库，当前开发数据库未执行 destructive downgrade；
- Workflow 审计/Outbox 事实存在，数据库 trigger 阻止 `workflow_task_events` 更新；OpenAPI/Schema/SDK/UI 使用同一契约；
- 官方 Temporal SDK time-skipping 测试首次本地初始化在 296 秒内未完成并被中止；2026-08-25 修正测试 Activity 类型并为 test-server 设置显式缓存目录后，本地真实执行 `1 passed`，GitHub Actions 独立 `temporal-time-skipping` job 在 run `32808198635` 通过，本条件项关闭；
- 用户已明确授权提交并 push。run `32808198635` 的 quality、time-skipping、Compose integration、四个 application-image 与 RustFS approval 共八个 job 全部通过；双架构 CycloneDX SBOM、可修复 HIGH/CRITICAL CVE 阻断证据、Cosign 签名与验证均成功并上传制品。
- 用户于 2026-08-25 正式验收 M2；该验收关闭 M2 阶段，不构成 M3 下发授权。
