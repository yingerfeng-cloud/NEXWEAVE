# NEXWEAVE M0-Lite（LL0）：本地轻量纵向闭环任务书 V1.0

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 执行轨道：Local Lite 本地轻量版  
> 建议周期：分阶段执行，以实际验收为准  
> 目标设备：Windows 11、4 核 8 线程、8 GB 内存、无独立 GPU  
> 上位基线：NEXWEAVE PRD V1.0、完整分阶段开发任务总纲 V1.0、M-1/M0—M15 任务书  
> 阶段原则：先形成可在本机真实使用的业务闭环，再以同一契约迁移到 Local Real、Docker Compose 和 Kubernetes

---

## 1. 用户需求摘要

1. 先开发一个能够在当前本机启动、操作和持久化数据的 NEXWEAVE Local Lite 版本。
2. Local Lite 范围内的业务功能必须真实执行，不得以静态页面、固定 JSON 或伪造成功状态代替后端流程。
3. 必须真实跑通以下核心纵向闭环：

   `资料导入 → 文档解析 → Schema 约束 → 知识编译 → Evidence 绑定 → 人工审核 → 质量评估 → 不可变 Release → 查询/问答与 Citation`

4. 当前阶段允许使用适合单机的轻量基础设施实现，但业务代码不得绑定这些实现。
5. 后期必须能够按同一领域模型、API、事件和工作流契约迁移到：
   - Docker Compose；
   - PostgreSQL；
   - RustFS；
   - Redis；
   - Temporal；
   - 独立 API、Web 和 Worker；
   - 真实 E2E；
   - 百万实体性能验证；
   - Kubernetes、高可用和灾备。
6. Local Lite 不得形成一套与 R1/R2/R3 平行的产品内核，也不得降低原任务总纲的正式验收门禁。

---

## 2. 阶段定位与原路线关系

M0-Lite 是原 M-1 与正式 M0—M15 路线之间的补充执行轨道，不替代任何正式 Milestone。

- M0-Lite 可以证明本地业务闭环、产品交互、领域规则和适配器契约可用。
- M0-Lite 通过，不等于正式 M0、R1、R2 或 R3 通过。
- 正式 M0/R1 仍须按当前批准基线使用真实 PostgreSQL、RustFS、Redis、Temporal 等依赖完成集成和 E2E 验收。
- 百万实体、Kubernetes、高可用、灾备和生产性能仍在后续专用环境验收。
- M0-Lite 产出的领域对象、API、事件、Release 语义和迁移资产必须成为后续正式工程的直接输入，不得推倒重建。

推荐执行顺序：

`M-1 基线 → M0-Lite/LL0 → Local Real → 正式 M0/R1 集成门禁 → R2/R3`

---

## 3. “真实跑通”的定义

Local Lite 中的“真实”必须同时满足：

1. Web 页面通过真实 API 读写数据，不读取静态演示数据作为业务结果。
2. 数据写入持久化存储，进程和电脑重启后仍可恢复。
3. 每个长任务真实记录任务、步骤、输入、输出、错误、重试次数和状态变化。
4. 导入的原始文件真实保存字节、哈希、版本和来源信息。
5. 编译结果真实经过 Schema 校验并生成可审查的 Entity、Relation、Claim、Evidence 或 WikiPage 草稿。
6. Evidence 能定位到 SourceVersion 中的页码、段落、字符范围或等价锚点。
7. 审核、批准、驳回、冲突处理和发布门禁由后端真实执行。
8. Release 一经发布不可原地修改；修正生成新版本，查询默认只读取正式 Release。
9. 查询或问答返回实际检索结果，并记录 Release、Citation、模型/策略版本和审计信息。
10. 自动化 E2E 从资料导入开始，通过正式查询结束，并验证重启恢复和关键失败分支。

以下实现允许作为 Local Lite 的真实本地 Provider，但不得声称与生产基础设施等价：

- SQLite 关系数据库；
- 本地文件系统对象存储；
- 进程内缓存；
- 数据库持久化的本地 Workflow Runner；
- SQLite FTS/本地检索 Provider；
- 确定性本地编译 Provider；
- 经 Model Gateway 调用的可选远程模型 Provider。

---

## 4. Local Lite 功能范围

### 4.1 必须交付的业务能力

1. **本地身份与空间**
   - 本地管理员初始化；
   - 用户、角色、知识空间和基础权限；
   - 单部署可保留 `tenant_id`、`space_id`，不得硬编码单租户语义；
   - 权限校验在 API 服务端执行并写入审计。

2. **资料中心与版本**
   - 导入 TXT、Markdown、PDF 中至少两种格式，其中必须包含 Markdown 或 TXT；
   - 保存原始文件、SHA-256、来源、密级、SourceDocument 与 SourceVersion；
   - 相同内容幂等识别，新内容形成新版本；
   - 支持查看解析状态、原文和锚点。

3. **文档解析**
   - 解析为统一 Block/Segment；
   - 保存顺序、段落、字符范围以及可获得的页码信息；
   - 解析失败、部分成功和重新解析有真实状态；
   - Parser 通过 Provider 接口接入。

4. **Schema 与知识编译**
   - 创建和版本化 SchemaDefinition/SchemaVersion；
   - 定义最小 EntityType、RelationType、Claim 和 PageTemplate；
   - 未绑定有效 SchemaVersion 的编译不得进入正式流程；
   - 支持确定性本地编译 Provider；
   - 预留并可配置真实远程 LLM Provider，但密钥不得进入仓库；
   - 保存 ModelProfile、PromptVersion、CompileJob 和 CompileStep。

5. **Wiki、Evidence 与 Conflict**
   - 生成、编辑和版本化 WikiPage 草稿；
   - Claim 和关键 Relation 必须绑定 Evidence；
   - Evidence 可回到 SourceVersion 原文位置；
   - 新旧知识不一致时创建 Conflict，不静默覆盖。

6. **审核与质量**
   - 创建 ReviewTask；
   - 支持提交、批准、驳回、要求补充资料和重新提交；
   - 记录 ReviewAction、Approval、责任人和时间；
   - 阻断冲突、缺失证据或 Schema 不合规时禁止发布；
   - 执行最小 EvaluationSuite/EvaluationRun 并保存结果。

7. **Release 与查询**
   - 创建发布候选、执行门禁、发布不可变 Release；
   - 支持历史 Release 查看和服务指针回滚；
   - 支持关键词、实体或基础关系查询；
   - 问答或查询结果必须返回 Release 标识与 Citation；
   - Evidence 不足时明确返回不确定或不可回答，不生成伪引用。

8. **审计与可观察性**
   - 登录、导入、编译、审核、批准、发布、回滚、查询和配置变更写入 AuditLog；
   - API 和 Workflow 使用 correlation_id；
   - 本地日志不得输出密钥、原始密码或未脱敏敏感内容；
   - 提供 API、Web、数据库和 Worker 的健康状态。

### 4.2 Web 必须覆盖的最小页面

- 登录/本地初始化；
- 工作台；
- 知识空间；
- 资料列表、导入、版本与原文查看；
- Schema 列表、编辑与版本；
- 编译任务与步骤；
- Wiki 草稿、Evidence 和 Conflict；
- 审核中心；
- 质量检查；
- Release 管理；
- 查询/问答与 Citation；
- 审计日志；
- 本地系统设置与 Provider 状态。

所有页面必须覆盖加载、空状态、权限拒绝、失败、重试和刷新恢复。

---

## 5. 本阶段明确不验收的内容

以下内容可以保留接口、配置和文档，但不得以 Local Lite 结果声称完成：

- Docker Compose 编排；
- PostgreSQL 生产语义、pgvector 和数据库高可用；
- RustFS/S3 一致性、生命周期和多节点能力；
- Redis 分布式锁、缓存一致性、Pub/Sub 或 Stream；
- Temporal Server 的 Replay、Worker 故障转移、长时间定时器和集群恢复；
- OpenSearch、Milvus、Neo4j、NebulaGraph；
- 百万实体和数百万关系性能；
- 多节点并发、弹性扩缩容和容量结论；
- Kubernetes、镜像供应链、离线镜像仓库；
- 高可用、跨机灾备、RPO/RTO 和生产恢复演练；
- 国产数据库、中间件、操作系统和浏览器的正式兼容认证；
- 商业 SLA、规模试点和运维移交。

---

## 6. 建议技术基线

以下为 M0-Lite 的拟定实现基线，须在编码前通过 ADR 确认：

- 后端：Python 3.12、FastAPI、Pydantic、SQLAlchemy 2、Alembic；
- 前端：TypeScript、React、Vite；
- 本地数据库：SQLite，开启外键约束和 WAL；
- 对象存储：应用数据目录下的内容寻址本地文件存储；
- Workflow：独立本地 Worker + 数据库持久化状态机；
- 缓存：进程内有界缓存；业务正确性不得依赖缓存；
- 检索：SQLite FTS 或等价本地 Provider；
- 模型：确定性本地 Provider + 可选远程 Model Gateway；
- 测试：Pytest、前端单元测试、API 契约测试和浏览器 E2E；
- 工程：Python/TypeScript Monorepo。

若实际依赖对 Python 3.12 存在阻塞，可在 ADR 中调整版本；不得直接使用系统 Python 和全局包作为可复现环境。

---

## 7. 工程与适配边界

建议目录：

```text
apps/
├── api/
└── web/
workers/
└── local/
packages/
├── domain/
├── contracts/
├── application/
├── sdk/
└── providers/
    ├── persistence_sqlite/
    ├── object_store_local/
    ├── workflow_local/
    ├── cache_local/
    ├── search_local/
    └── model_local/
domain-packs/
infra/
├── local-lite/
└── compose/                # 仅保留后续入口，本阶段不要求可用
tests/
├── unit/
├── contract/
├── integration_local/
└── e2e_local/
docs/
```

必须冻结以下 Port/Provider 契约：

- `PersistencePort`；
- `ObjectStorePort`；
- `WorkflowPort`；
- `CachePort`；
- `ParserPort`；
- `ModelGatewayPort`；
- `SearchPort`；
- `VectorPort`；
- `GraphQueryPort`；
- `IdentityPort`；
- `AuditPort`。

架构门禁：

1. `domain` 和 `contracts` 不得依赖 FastAPI、SQLAlchemy、SQLite、Temporal、Redis、RustFS 或模型厂商 SDK。
2. SQLite SQL、文件路径和本地线程实现只能出现在对应 Provider 中。
3. Workflow 定义必须保持确定性；文件、网络、数据库和模型调用必须封装为 Activity/Task 边界。
4. 正式状态不得只保存在缓存或前端状态中。
5. Provider 必须通过统一契约测试，后续生产 Provider 使用同一套测试。
6. API、事件、错误码、ID、版本和审计字段不得因运行配置不同而改变语义。

---

## 8. 数据与迁移零债务要求

1. 核心对象沿用总纲，不建立 Lite 专用同义对象。
2. 所有核心对象从第一版包含 `id`、`tenant_id`、`space_id`、状态、版本、创建者、创建时间和更新时间。
3. ID、UTC 时间、枚举、JSON、唯一约束和乐观锁采用可迁移到 PostgreSQL 的表示。
4. 所有数据库变更通过 Alembic 管理；不得用启动脚本静默改表。
5. 不得在 domain/application 中编写 SQLite 方言 SQL。
6. 本地对象 key 使用稳定逻辑标识，不暴露绝对磁盘路径给领域层和 API。
7. 保存 SourceVersion checksum、Release manifest、PromptVersion、ModelProfile 和索引配置，以支持重建。
8. 编写 SQLite → PostgreSQL 数据迁移设计和校验清单，但本阶段不要求执行生产迁移。

---

## 9. 本地运行要求

1. 不依赖 Docker、WSL、PostgreSQL、Redis、RustFS 或 Temporal 安装。
2. 提供 PowerShell 友好的一键初始化与一键启动命令。
3. 首次启动自动创建应用数据目录，但不得覆盖已有数据。
4. 支持开发、测试和演示三个本地配置，数据目录互相隔离。
5. 支持干净安装、增量升级、备份导出和本机恢复。
6. 默认资源目标：空闲状态不持续占满 8 GB 内存，少量测试数据下保持可交互。
7. 可配置使用远程 LLM；未配置模型凭据时仍可通过确定性本地 Provider 跑通验收链路。
8. `.env.example` 只包含变量名和说明，不包含真实凭据。

---

## 10. 分阶段实施计划

M0-Lite 不得一次性大爆炸交付，按以下子阶段逐一执行和验收：

### LL-0：基线、工程骨架与本地启动

- 核验 M-1 已完成并通过必要治理基线；
- 冻结建议技术栈和 Port/Provider ADR；
- 建立 Monorepo、API、Web、Worker 和测试骨架；
- 实现配置、健康检查、SQLite 迁移和本地数据目录；
- 一条命令启动最小 API/Web/Worker。

### LL-1：身份、空间、资料与解析

- 本地身份、权限、空间和审计；
- 资料导入、原始字节、版本、checksum；
- 文档解析、统一 Segment 和 SourceAnchor；
- 对应真实 Web 页面和本地 E2E。

### LL-2：Schema、编译、Wiki 与 Evidence

- Schema Studio 最小能力；
- 本地确定性编译 Provider；
- 可选远程 Model Gateway；
- Wiki 草稿、Entity、Relation、Claim、Evidence 和 Conflict；
- 编译任务状态、失败、重试和重启恢复。

### LL-3：审核、评估与不可变发布

- ReviewTask、ReviewAction、Approval；
- 最小质量评估；
- 发布门禁、不可变 Release、历史版本和回滚；
- 权限与审计闭环。

### LL-4：查询、问答与完整 E2E

- 基础全文、实体和关系查询；
- 基于固定 Release 的问答或可信回答；
- Citation 和不确定性；
- 完整 `Source → Parse → Compile → Review → Evaluate → Release → Query` E2E。

### LL-5：迁移准备与 Local Real 交接

- Provider 契约测试；
- PostgreSQL、RustFS、Redis、Temporal 适配设计；
- Docker Compose 服务拓扑和配置映射；
- SQLite/本地文件导出与迁移校验方案；
- 输出 Local Real 下一阶段任务书输入，不自行进入下一阶段。

每个子阶段完成后必须停止、回报、验收，再进入下一阶段。

---

## 11. 测试体系

### 11.1 必须执行

- 单元测试：领域规则、状态机、权限、Evidence、发布门禁；
- 架构测试：依赖方向和 Provider 隔离；
- 契约测试：OpenAPI、事件、Provider 和错误码；
- 本地集成测试：SQLite、本地对象存储、本地 Workflow Runner；
- 前端测试：关键页面、权限、错误、刷新和路由；
- 本地 E2E：至少覆盖成功链路、审核驳回、证据缺失、冲突阻断和重启恢复；
- 迁移测试：SQLite 正向迁移、回滚验证和旧版本数据升级；
- 安全测试：越权、路径穿越、恶意文件名、Prompt 注入、凭据泄漏。

### 11.2 测试分级

- `unit`：无外部依赖，快速执行；
- `contract`：验证 Port、API 和事件契约；
- `integration-local`：使用真实 Local Provider；
- `e2e-local`：使用真实 Web/API/Worker 和持久化数据；
- `integration-real`：后续连接 PostgreSQL/RustFS/Redis/Temporal；
- `performance`、`ha-dr`：后续专用环境执行。

不得用 `e2e-local` 结果替代 `integration-real`、性能或灾备报告。

---

## 12. Local Lite 总体验收标准

- [ ] 一条命令能在本机启动 API、Web 和本地 Worker。
- [ ] 电脑重启后可恢复业务数据、原始文件、任务状态和 Release。
- [ ] Web 全部关键页面由真实 API 驱动。
- [ ] 资料导入到正式 Release 和查询形成真实完整闭环。
- [ ] Source、Schema、Prompt、Model、Evidence、Review、Release 和 Citation 可追溯。
- [ ] 未审核草稿不能被正式查询读取。
- [ ] 缺少 Evidence、存在阻断 Conflict 或 Schema 不合规时无法发布。
- [ ] Release 不可原地修改，回滚不篡改历史版本。
- [ ] 本地任务支持可观察的失败、重试和重启恢复。
- [ ] 所有 Local Provider 通过统一契约测试。
- [ ] 无业务模块直接依赖 SQLite、文件系统、本地缓存或本地线程实现。
- [ ] 自动化测试、前端构建、迁移和安全检查通过。
- [ ] 已明确列出与真实 PostgreSQL、RustFS、Redis、Temporal 的差距。
- [ ] 未声称完成百万实体、Kubernetes、高可用或灾备验收。

---

## 13. 禁止事项

1. 不得用静态 JSON、固定 fixture 响应或纯前端状态声称业务功能完成。
2. 不得将 SQLite、本地文件或本地 Workflow Runner 写入领域契约。
3. 不得以缓存作为正式业务状态权威源。
4. 不得跳过权限、审计、Evidence、Review 或 Release 门禁。
5. 不得把草稿内容暴露给正式查询。
6. 不得伪造模型输出、引用、测试结果、性能数据或恢复结果。
7. 不得在仓库中保存 API Key、密码、Cookie、真实敏感资料或内部地址。
8. 不得以 Local Lite 验收替代原 M0—M15 验收。
9. 不得自行进入 Docker Compose、Kubernetes 或下一正式 Milestone。
10. 不得覆盖用户已有文件、重置仓库、自动 push 或伪造 Git 身份。

---

## 14. 关键 ADR 与待批准项

编码前必须形成并批准至少以下决策：

1. M0-Lite 是否正式使用 Python 3.12 + FastAPI；
2. 前端是否使用 React + TypeScript + Vite；
3. SQLite 是否仅作为 Local Lite 权威状态实现；
4. 本地 Workflow Runner 的持久化、重试、取消和恢复语义；
5. 确定性本地编译 Provider 的能力边界；
6. 远程模型凭据、密级和数据出域策略；
7. 本地检索能力与正式 pgvector/OpenSearch 能力的差异；
8. SQLite → PostgreSQL 数据迁移和双环境契约测试策略；
9. Local Lite 用户模型与后续企业 IAM 的映射；
10. Local Lite 版本号、数据目录和升级兼容策略。

在这些决策批准前，可以建立文档与无争议工程骨架，但不得静默固化关键技术选择。

---

## 15. Codex 子阶段最终回报格式

```markdown
# NEXWEAVE M0-Lite / LL-x 执行结果

## 1. 总体结论
- 子阶段：通过 / 有条件通过 / 不通过
- 是否可进入下一子阶段：是 / 否
- Git 基线：提交哈希 / 未提交及原因

## 2. 实际完成范围
- 逐项对应本任务书和当前 LL-x 子任务说明。

## 3. 新增或修改文件
- 路径、用途、对应需求或验收项。

## 4. 真实功能与本地替代实现
- 真实业务能力：
- Local Provider：
- 与生产 Provider 的已知差距：

## 5. 测试与验证
- 命令：
- 结果：
- 未执行项及原因：

## 6. 数据、迁移与恢复
- 数据库迁移：
- 本地数据恢复：
- 后续 PostgreSQL/对象存储迁移影响：

## 7. 安全、权限、审计、Evidence 与 Release 检查
- 结论与证据：

## 8. 风险与遗留项
- P0：
- P1：
- P2：

## 9. 停止声明
已停止在 LL-x，未自行进入下一子阶段、正式 M0 或 Docker/Kubernetes 阶段。
```

---

## 16. 本任务书完成后的下一步

1. 由用户/架构负责人评审第 14 章 ADR 与待批准项。
2. 若批准 Local Lite 路线，单独下发 LL-0 子任务。
3. LL-0 只建立治理基线、工程骨架、本地启动和健康检查，不直接实现全部业务功能。
4. LL-0 验收后，依次执行 LL-1—LL-5。

本任务书发布后应停止，不得自动开始 LL-0 编码。
