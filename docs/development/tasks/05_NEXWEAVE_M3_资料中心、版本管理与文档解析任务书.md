# NEXWEAVE M3：资料中心、版本管理与文档解析任务书

> 产品：NEXWEAVE｜织界——企业级 LLM Wiki 标准化平台  
> 产品版本：R1：可信知识闭环与联合试点版  
> 建议周期：4—5 周
> 执行对象：Codex  
> 状态：2026-08-25 已按正式 M3 下发指令完成执行前校准
> 权威增量：ADR-0021；已验收 M0—M2 基线
> 当前边界：任务书/ADR/治理校准已完成；用户已在同一指令中明确授权按本任务书继续正式实施 M3
> 阶段原则：后续实施只执行本 Milestone，完成后停止

---

## 1. 阶段定位与可信边界

M3 建立“受控上传 → 不可变 Raw → 安全扫描 → 版本化解析 → 可授权预览 → 可复现 SourceAnchor”的首条真实知识资料链路，为 M5/M6 的编译、Evidence 和 Citation 提供固定输入。

M2 的 `SourceIngestionWorkflow` 仅为已验收的可靠内核 Stub：`nexweave.source-ingestion.v1`、`STUB_SUCCEEDED` 和通用 WorkflowTask 成功均不代表文件已扫描、解析或生成 SourceAnchor。M3 必须建立真实 Source/Parse 业务聚合与 v2 Workflow，不能把 M2 结果迁移或改名为业务完成。

M3 仍不生成知识草稿、Claim、Evidence、Conflict 或 Release。DocumentSegment 和 SourceAnchor 是 Raw 的版本化派生/定位基础，不是已审核知识，也不能被业务应用或 GridCrew 当作正式内容消费。

---

## 2. 权威资料与前置条件

实施前必须完整读取并核对：

1. 用户当前指令、本任务书和根 `AGENTS.md`；
2. ADR-0001—ADR-0021、`ARCHITECTURE_BASELINE.md`、`PRODUCT_BASELINE.md`；
3. `PROJECT_STATUS.md`、`OPEN_QUESTIONS.md`、需求追踪矩阵及 M2 执行/验收资料；
4. API、Event、Workflow、Domain、Data、State/Permission/Error、Security、Dependency、Migration 与 Quality baseline；
5. PRD 8.3、原型“资料中心/上传”交互目标和完整开发总纲；原型数据、500 MB 文案、自动编译与连接器入口不构成功能事实或批准阈值。

必须满足：

- M2 已正式验收，M1 身份/空间/RBAC+ABAC/Audit/Outbox/幂等/ObjectStoragePort 与 M2 Temporal/任务投影可运行；
- `0001`—`0003` 历史迁移保持不变；
- M2 v1 Workflow 历史具备 Replay 基线；
- 工作区修改已盘点并保护；
- OQ-PARSE-001 已由 ADR-0021 冻结。

若真实 RustFS、Temporal、PostgreSQL 或可接受的真实恶意文件扫描 Provider 无法运行，相关纵向验收为 P0 阻塞；不得以 ManagedObject、Stub Scanner、固定文本或内存状态冒充 Source/解析完成。

---

## 3. 阶段目标

1. 实现 PDF、DOCX、Markdown、TXT、CSV、XLSX 的受控导入、Raw 版本、解析、批次和预览。
2. 实现 SourceDocument、SourceVersion、SourceUploadSession、ImportBatch、ParseJob、DocumentSegment、SourceAnchor 与 SourceInvalidation 的真实领域/数据库/API 闭环。
3. 实现 ParserPort/OcrPort、统一文档模型和隔离的 Parser/OCR Worker adapter 边界。
4. 实现文件安全、checksum 幂等、疑似重复提示、版本替代、归档/失效、失败/部分成功、retry/reparse 和 Anchor 失效/重定位。
5. 把 M2 可靠内核安全演进为 `nexweave.source-ingestion.v2` 业务 Workflow，同时保留 v1 Replay。
6. 交付真实 API 驱动的资料中心、版本/解析详情和原文/Anchor 预览。

---

## 4. 范围与非范围

### 4.1 M3 范围

- 单文件与批量文件上传；上传会话、完成校验、批次逐项结果；
- 文件名、来源说明、来源等级展示值、标签、密级、有效期元数据；来源等级在 M3 只作可审计元数据，不得自动等同事实置信度；
- Raw 私有存储、checksum/size/MIME/魔数校验、同 key 条件写、受控下载；
- SourceDocument 版本链、显式替代、归档、SourceVersion 失效记录；
- 文件白名单、安全扫描、活动内容/宏/OOXML 解压风险检查和解析隔离；
- 六类文件的统一 Segment/Block 输出；扫描 PDF 的真实检测与 OCR 能力缺口表达；
- ParseJob、结果版本、失败单元、retry、reparse、active/latest 解析指针；
- page/block/character-range/table-cell/bbox SourceAnchor、预览高亮、失效检测与重定位关系；
- Web、OpenAPI、事件 JSON Schema、Python/TypeScript SDK、迁移、审计、Outbox、可观测性、测试和文档。

### 4.2 明确非范围

- URL/网页抓取、数据库/API/S3/Git/邮件等 Connector，同步计划和“管理连接器”（M8）；
- 手工录入、旧二进制 DOC/XLS、DOCM/XLSM、压缩包、独立图片、音视频；
- 解析后自动编译、批量编译、Schema 绑定、模型/Prompt 调用、实体/关系/页面生成（M4/M5）；
- Claim、Evidence、Conflict、Review、质量门禁、Release、Query/Citation（M6/M7）；
- GridCrew/Obsidian、客户/RCA 专用解析分支或外部资料回流（M8/M9）；
- 生产级 OCR 质量承诺。M3 只要求 OcrPort 与扫描检测；只有引入获批并真实运行的 OCR Provider 后，才可把 OCR 输出列为完成证据；
- 物理删除 Raw、历史解析、Anchor、Audit 或 Outbox；
- 将原型中的固定数据、500 MB 文案、来源枚举或自动编译交互直接固化为产品策略。

---

## 5. 不可变约束

1. Raw First：原始字节、对象版本、checksum、来源与密级不可被 Parser、OCR、LLM 或编辑接口覆盖。
2. Gateway First：业务只依赖 ObjectStoragePort、MalwareScannerPort、ParserPort、OcrPort；厂商库只存在于 adapter/Worker。
3. Reliable Workflow：Temporal 是 Parse 执行权威；DB 只保存业务事实、结果和可修复查询投影。
4. Version Reproducibility：ParseJob 固定 parser/OCR/config/document-model/locator 版本；reparse 不覆盖旧结果。
5. Evidence Native：Anchor 必须固定 SourceVersion、Raw checksum 与 ParseJob；临时页码/全文搜索不是唯一定位。
6. 安全默认拒绝：所有上传、下载、预览、解析、重试、替代、失效和归档由服务端重新校验 tenant/space/状态/密级/权限。
7. 不静默合并：checksum 命中、疑似重复、版本替代、部分失败和重定位都形成显式结果与审计。
8. M3 不越界：Segment/Anchor 不是 Evidence，Parse 成功不是 Compile/Review/Release 成功。

---

## 6. 领域对象与权威关系

| 对象 | 责任与不可变规则 | 关键关系/权威 |
|---|---|---|
| SourceUploadSession | 分配 Source/Version ID、对象 key、过期和 multipart/单次上传技术状态 | DB 会话 + RustFS 临时/目标对象；不冒充 SourceVersion |
| ImportBatch | 聚合多个独立上传项及逐项结果 | DB；批次状态不覆盖单项状态 |
| SourceDocument | 逻辑资料身份、元数据、版本替代链入口与归档 | DB；tenant/space 范围，强 ETag |
| SourceVersion | 不可变 Raw 元数据、checksum、key/version、密级、替代关系、active/latest ParseJob | DB 元数据 + RustFS 字节；内容不可修改 |
| SourceInvalidation | 版本失效原因、actor、policy/version、时间与影响事实 | DB append-only；不删除或改写 SourceVersion |
| ParseJob | 一次固定配置的解析业务执行与结果清单 | Temporal 执行 + DB 业务结果/投影；每次 reparse 新建 |
| ParseFailureUnit | 页/表/工作表/块级稳定错误、重试性与安全诊断 | ParseJob 内追加事实 |
| DocumentSegment | 有序、版本化、可重建解析块 | 绑定 SourceVersion + ParseJob；不是知识/Evidence |
| SourceAnchor | 复合定位值、excerpt hash、状态和重定位链 | 绑定 SourceVersion/checksum/ParseJob；DB 权威 |
| WorkflowTask/Step/Event | M2 通用执行查询投影和追加日志 | 与 ParseJob 关联；不替代上述业务聚合 |

所有对象按 ADR-0013 使用 UUIDv7、tenant/space、UTC、actor/audit/correlation 元数据；可变聚合使用强 ETag/version，不可变事实不伪造更新字段。

---

## 7. 状态机与命令语义

### 7.1 状态词汇

| 聚合 | 状态 | 约束 |
|---|---|---|
| SourceUploadSession | `INITIATED/UPLOADING/COMPLETING/COMPLETED/ABORTED/EXPIRED` | 完成/终止后不可继续写；multipart 失败必须 abort |
| ImportBatch | `CREATED/UPLOADING/PROCESSING/PARTIAL/SUCCEEDED/FAILED/CANCELED` | 单项独立提交；部分成功不回滚成功项 |
| SourceDocument | `REGISTERED/ACTIVE/ARCHIVED` | 归档不删除 Raw；资料/版本失效只追加 SourceInvalidation；M3 不提供物理删除 |
| SourceVersion | `STORED/PARSING/PARTIAL/PARSED/FAILED/SUPERSEDED` | Raw 不变；失效是正交 append-only 事实 |
| ParseJob | `CREATED/QUEUED/RUNNING/PARTIAL_FAILED/FAILED/SUCCEEDED/CANCELED` | Temporal 推进；终态结果不改写 |
| SourceAnchor | `VALID/STALE/UNRESOLVED/REVOKED` | 重定位新建 Anchor；无 `INVALID/RELOCATED` 状态 |

### 7.2 转移与重试

```text
Upload: INITIATED → UPLOADING → COMPLETING → COMPLETED
                     └──────────────→ ABORTED / EXPIRED

Initial parse: STORED → PARSING → PARSED | PARTIAL | FAILED
ParseJob: CREATED → QUEUED → RUNNING → SUCCEEDED | PARTIAL_FAILED | FAILED | CANCELED
Version: old SourceVersion → SUPERSEDED only after an explicit replacement is registered
```

- 首次解析成功/部分成功设置 active/latest ParseJob；首次无可用输出失败才把 SourceVersion 置为 FAILED。
- 已有 active 结果时，reparse 运行不把 SourceVersion 降为 PARSING；成功后切换 active，失败/取消只更新 latest 并保留旧 active。
- retry 保持 ParseJob、输入和配置不变，按错误分类重试同一业务操作；parser/config/OCR 策略变化必须 reparse 并新建 ParseJob。
- `PARTIAL_FAILED` 必须至少有一个真实可用 Segment，并列出全部失败单元；否则为 FAILED。
- checksum 不匹配、恶意文件、类型拒绝、资源上限和权限/策略错误不可原样自动重试；对象存储/Worker 瞬态错误可使用相同幂等键退避重试。
- 取消不删除 Raw 或已写事实；未完成结果不得切换 active 指针。
- 替代创建新 SourceVersion；单版本失效创建 SourceInvalidation；逻辑资料整体撤销/归档只改变 SourceDocument 生命周期。四者不得混用。

---

## 8. 文件存储与安全

1. canonical Raw key 必须为 `raw/v1/{tenant_id}/{space_id}/{source_document_id}/{source_version_id}/{sha256}`；原始文件名不进入 key。
2. 上传完成由服务端重新读取并验证 SHA-256、size、扩展名/MIME/魔数、对象 version 和条件写事实；客户端声明不可信。
3. 同一幂等键/同一规范请求返回原结果；同 key/不同请求返回 `IDEMPOTENCY_KEY_REUSED`。相同字节只提示，不能跨对象/范围静默合并。
4. 白名单仅为 PDF、DOCX、Markdown、TXT、CSV、XLSX；DOC/XLS、宏格式、活动内容、嵌入脚本、可执行文件和普通压缩包明确拒绝。
5. 真实 MalwareScannerPort 是解析前门禁；M1 Stub Scanner 不构成 M3 验收。感染、扫描失败和扫描不可用必须可区分，只有通过策略的 Raw 才能进入 Parser。
6. DOCX/XLSX 按不可信 OOXML 压缩容器处理，限制压缩条目、总展开大小、压缩比、嵌套深度、关系/外链和嵌入对象。
7. Parser/OCR 运行边界默认无出站网络、非 root、只读 Raw 输入、独立临时目录，并限制 CPU、内存、时间、页数、工作表/行列和输出大小。
8. 下载先重新授权，再签发短期、限定 method/key 的 URL 或受控流；桶/对象私有，客户端无长期 S3 凭据。水印只在受控 `DownloadTransform/Policy` 接口预留，不伪造未实现的文件水印能力。
9. Preview 必须净化 HTML/Markdown/办公内容，不执行脚本、宏、外链或嵌入对象；Content-Type、CSP、下载 disposition 与缓存策略安全可测。
10. 日志、Problem、事件、Trace、指标和普通 Audit 不保存 Raw 正文、token、凭据或未脱敏长摘录。

文件大小、页数、解压比等数值是可配置部署策略，必须提供有界默认值、诊断与边界测试；不得把原型的 500 MB 文案当成已批准的固定产品阈值。

---

## 9. Parser/OCR SPI 与统一文档模型

### 9.1 Port/SPI

- `ParserPort`：capabilities/probe/parse；输入为受控对象引用、固定配置与预算，输出为版本化 result manifest、Segments、失败单元和安全统计。
- `OcrPort`：capabilities/recognize；只接收受控页图/区域引用，输出文本、页码、normalized bbox、置信度和 provider/config 版本。
- Provider 注册表以 MIME + capability 选择 adapter，禁止业务层按客户/行业分支；未知/歧义类型返回稳定错误。
- Parser/OCR 返回值先通过 contracts 校验、数量/大小限制和 checksum，再由幂等 Activity 持久化。

### 9.2 统一输出

Segment 至少包含：稳定 ID、source_version_id、parse_job_id、sequence、block_type、structure_path、normalized_text 或受控派生对象引用、text checksum、page/sheet/table 元数据、locator 集合、parser/config/document-model 版本。

M3 至少支持 heading、paragraph、list、table、table-cell、image/figure-reference、page-boundary；CSV/XLSX 保留 sheet/table/row/column 位置，不得只拼成整篇纯文本；PDF/DOCX 保留段落、页/表等可验证结构。

规范化算法、字符偏移基准和 locator version 必须写入 contract 与 golden fixture；升级算法时提升版本，禁止让旧 Anchor 悄然漂移。

### 9.3 扫描 PDF/OCR

- 使用真实 PDF 页面文本/对象信息检测“扫描型/无文本页”，不得靠文件名或固定 fixture 标志假装检测；
- 无真实 OCR Provider 时，记录页级 `OCR_REQUIRED`，可保留页面边界/元数据并进入 `PARTIAL_FAILED`；UI 明示未提取正文；
- 若实施阶段选择 OCR Provider，必须先更新依赖基线、许可证/模型来源、CPU/内存/语言包、离线与替代方案，并以真实 Provider E2E 验证；Mock 仅可用于单元测试。

---

## 10. SourceAnchor、失效与重定位

1. M3 新 Anchor 必填 `source_version_id`、`source_checksum`、`parse_job_id`、`locator_version`、`excerpt_hash` 和至少一种 locator。
2. 复用现有 locator v1：page、block、character range、table cell、normalized top-left bbox；段落由稳定 block ID 表达。时间 locator 保持契约兼容但不属于 M3 文件验收。
3. preview/highlight 通过 `anchor_id` 读取并重新授权，返回 `VALID/STALE/UNRESOLVED/REVOKED` 与每个 locator 的命中结果；不得让调用者提交任意本机路径或对象 key。
4. reparse 后对旧 Anchor 做 checksum/excerpt/structure 验证。重定位成功创建新 Anchor 并写 `relocated_from_anchor_id`；失败保留旧 Anchor 并标记 STALE/UNRESOLVED。
5. 版本替代不会把旧 Anchor 绑定到新 SourceVersion；新版本必须生成自己的 Anchor。失效/授权撤销保留历史事实，但正文预览和下载拒绝或遮蔽。
6. M3 只验证定位基础；不得创建 Evidence/Citation 或声称正式知识已获得证据。

---

## 11. Workflow 与 Activity

### 11.1 兼容策略

- 保留 `nexweave.source-ingestion.v1` 及现有三步 Stub 注册/Replayer；禁止修改其历史语义或将结果回填为 Source 业务事实。
- M3 新任务使用 `nexweave.source-ingestion.v2`，Workflow ID 为 `source-ingestion/{tenant_id}/{parse_job_id}`；通用 WorkflowTask 的 business key 使用 ParseJob ID。
- v2 与 v1 必须同时通过 Replay/注册测试；v1 退役不属于 M3。

### 11.2 v2 确定性步骤

```text
load immutable refs
→ verify Raw metadata/checksum/type
→ malware/security scan
→ select parser capability
→ parse document
→ detect/optionally run OCR
→ validate result manifest
→ persist segments/anchors/failure units
→ evaluate relocation
→ finalize ParseJob/SourceVersion pointers
```

Workflow 仅编排输入引用、步骤、durable timer、取消、retry 分类和补偿意图；不得直接访问 DB、RustFS、网络、文件、系统时间、Parser 或 OCR。

### 11.3 Activity 要求

| Activity 类别 | 幂等键/输出 | 失败与补偿 |
|---|---|---|
| Raw 校验/扫描 | source version + checksum + policy version | checksum/恶意内容不可重试；不删除已登记 Raw |
| Parser/OCR | parse job + step + input/config hash | 心跳/资源上限；临时产物可清理，结果提交前不可见 |
| 结果持久化 | parse job + result manifest checksum | upsert 仅幂等同结果；异结果冲突，不覆盖旧结果 |
| Anchor/重定位 | parse job + locator/excerpt hash | 新建/追加关系；不改写历史 locator |
| 状态/指针 | parse job + terminal event key + ETag | 原子 DB + Audit + Outbox；失败可对账重放 |

每类 Activity 明确 start/schedule/heartbeat timeout、retry policy、non-retryable allowlist、取消行为、最大输出与可观测字段。Worker 重启、重复 Activity、API/Temporal/DB 崩溃窗口均须有恢复测试。

---

## 12. API、事件与 SDK

### 12.1 API 最小集合

| 方法与路径 | 语义 | 权限/并发 |
|---|---|---|
| `POST /spaces/{space_id}/source-import-batches` | 创建批次 | `source.upload` + Idempotency-Key |
| `POST /spaces/{space_id}/sources/uploads` | 创建 Source 上传会话/预分配 ID | `source.upload` + Idempotency-Key |
| `PUT /sources/uploads/{upload_id}/content` 或批准的 multipart 等价入口 | 条件上传字节 | 会话 token/权限；不可覆盖 |
| `POST /sources/uploads/{upload_id}/complete` | 服务端校验、登记 Raw、创建初始 ParseJob/v2 Workflow | Idempotency-Key；返回 source/version/parse job/workflow/run ID |
| `POST /sources/uploads/{upload_id}/abort` | 终止未完成会话并收敛批次单项 | `source.upload` + Idempotency-Key |
| `GET /spaces/{space_id}/sources` | 资料列表、过滤、稳定游标 | `source.read` + 密级 |
| `GET /sources/{source_id}` | 资料详情、版本链、批次/重复提示 | `source.read`；强 ETag |
| `POST /sources/{source_id}/archive` | 软归档 | `source.archive` + If-Match + key |
| `GET /sources/{source_id}/versions/{version_id}` | Raw/解析元数据、active/latest 指针 | `source.read` + 密级 |
| `GET /source-versions/{id}/content` | 受控下载 | `source.download` + 密级 + 审计 |
| `POST /source-versions/{id}/parse` | reparse：固定新配置并创建新 ParseJob | `source.parse` + If-Match + key |
| `POST /parse-jobs/{id}/retry` | 同配置可重试失败的新 Run/步骤恢复 | `source.parse` + If-Match + key |
| `POST /parse-jobs/{id}/cancel` | 取消未终态 ParseJob，保留 Raw 与既有 active 结果 | `source.parse` + If-Match + key |
| `GET /parse-jobs/{id}` | 状态、步骤、失败单元、配置/结果版本 | `source.read` |
| `GET /source-versions/{id}/segments` | active 或显式 ParseJob 的分页 Segment | `source.read` + 密级 |
| `GET /source-versions/{id}/preview?anchor_id={anchor_id}` | 净化预览与定位结果 | `source.read` + 密级；禁止任意路径 |
| `POST /source-versions/{id}/invalidate` | 追加失效事实 | `source.invalidate` + If-Match + key |

所有列表使用显式排序与 opaque cursor。所有错误为 `application/problem+json`；新增稳定错误至少覆盖 `SOURCE_TYPE_UNSUPPORTED`、`SOURCE_CHECKSUM_MISMATCH`、`SOURCE_MALWARE_DETECTED`、`SOURCE_SECURITY_POLICY_FAILED`、`PARSER_CAPABILITY_UNAVAILABLE`、`PARSER_RESOURCE_LIMIT_EXCEEDED`、`OCR_REQUIRED`、`PARSE_RESULT_INVALID`、`ANCHOR_UNRESOLVED`，并映射明确 HTTP/retry 规则。

Source 业务入口必须创建/控制 v2 Workflow；不得要求客户端通过通用 M2 `/workflow-tasks` Stub 创建 Source 业务结果。通用任务详情可作为关联执行视图。

### 12.2 事件

在业务事务内写最小 Outbox 事实：

- `io.nexweave.source.version-ready.v1`：Raw 已完成服务端校验并处于 STORED；`ready` 只表示可进入安全扫描/解析，不表示 clean、parsed 或 compile-ready；
- `io.nexweave.source.version-superseded.v1`；
- `io.nexweave.source.invalidated.v1`；
- `io.nexweave.parse.completed.v1`；
- `io.nexweave.parse.partial-failed.v1`；
- `io.nexweave.parse.failed.v1`。

Payload 仅含 tenant/space、source/version、parse job、状态、parser/config/result version、failure summary、Workflow/run、aggregate version和 correlation/causation；不得包含 Raw、长摘录或下载 URL。M3 只实现 transactional Outbox，不得声称 Broker 已发布/消费。

### 12.3 SDK

Python/TypeScript typed SDK 覆盖上传会话/完成、批次、列表/详情/版本、parse/retry、segments、preview、invalidate/archive；以提交的 OpenAPI/JSON Schema 为单一来源，并包含幂等键、ETag、分页、Problem code 与异步 ID 类型。

---

## 13. Web 与交互

1. `/sources`：真实资料列表、搜索/类型/状态/密级过滤、空/加载/错误/重试、批量导入入口和批次逐项结果。
2. `/sources/{source_id}`：元数据、权限、版本替代链、checksum、解析状态、active/latest ParseJob、失败单元、审计摘要和允许动作。
3. `/sources/{source_id}/versions/{version_id}`：Raw 元数据、Parse 历史、parser/config 版本、Segments、下载、reparse/invalidate。
4. `/source-versions/{version_id}/preview?anchor_id=...`：净化原文/派生预览、page/table/paragraph/bbox 高亮、locator 逐项结果和 STALE/UNRESOLVED/REVOKED 明示。
5. 深链接、刷新恢复、浏览器返回和 URL 筛选必须由 API 恢复；前端不以本地状态推进 Workflow 或授权。
6. 上传展示 checksum/扫描/解析阶段、逐文件错误、取消与可执行动作；部分成功不能用绿色“完成”替代失败详情。
7. 原型中的“管理连接器”“批量编译”“解析完成后自动编译”和知识产出计数在 M3 禁用或明确标注后续阶段，不得接 Mock。
8. 延续深色设计语言、键盘/焦点/ARIA、响应式和浏览器基线；服务端权限拒绝不能只靠隐藏按钮。

---

## 14. 数据库与迁移

新增单一 additive revision（建议 `0004_m3_source_parsing`），至少覆盖：

- `source_documents`、`source_versions`、`source_upload_sessions`；
- `source_import_batches` 与 batch item；
- `source_invalidations`；
- `parse_jobs`、`parse_failure_units`、`document_segments`、`source_anchors`；
- tenant/space 复合外键、UUIDv7、状态 check、SourceVersion checksum/key/version、版本替代无自环/唯一规则；
- ParseJob config/result checksum、active/latest 指针约束、Segment 顺序/范围、Anchor parse/source/checksum 一致性；
- append-only invalidation/解析事实、Audit/Outbox/Idempotency 关联和必要索引。

不得修改 `0001`—`0003`。M1 `ManagedObject` 不自动转成 SourceVersion，也不批量回填/删除；若提供显式迁入工具，必须走与新上传等价的校验、权限、审计和幂等链路，且不属于最低验收。

验证必须在精确命名的一次性真实 PostgreSQL 数据库执行 `base → head → 0003 → head`（或等价安全 down/up），证明 downgrade 不删除 M0—M2 数据；共享/生产数据库禁止用通用破坏性 migration-check。生产回滚必须先停写、备份 Source 元数据与 Raw manifest，并说明 v2 Workflow/新表的前向恢复策略。

---

## 15. 依赖与供应链

1. 新 Parser、文件类型检测、安全扫描、预览或可选 OCR 依赖在引入前记录：用途、精确版本、直接/传递许可证、维护状态、已知 CVE、资源/平台支持、离线/双架构能力、替代/移除方案。
2. 禁止来源未知、停止维护、执行宏/办公套件活动内容或默认联网的 Parser。需要系统二进制/语言包/模型时，镜像 digest、SBOM、许可证和构建来源纳入门禁。
3. Parser/OCR 依赖只进入 adapter/Worker；domain/contracts/application Port 不导入厂商 SDK。
4. Golden/恶意/畸形文档 fixture 必须合成或明确许可证、来源、checksum 和密级；不得提交客户、内部或未脱敏资料。
5. 更新 lockfile、Dependency Baseline、镜像 SBOM/CVE/Cosign gate 与替代矩阵；无批准例外的可修复 HIGH/CRITICAL 漏洞阻断验收。

---

## 16. 测试、E2E 与故障验证

### 16.1 自动化矩阵

- 单元：对象状态/转移、替代链、幂等/重复提示、partial/retry/reparse、active/latest 指针、Anchor 状态/重定位、权限和错误分支；
- 架构：domain/contracts/application 的厂商隔离，v2 Workflow 无 I/O/非确定性调用，Parser/OCR 仅 adapter；
- 契约：OpenAPI、事件、SDK、Parser/OCR SPI、统一文档模型、locator v1 与 Problem code；
- 集成：真实 PostgreSQL、RustFS、Temporal、真实 MalwareScanner 和各文件 Parser；
- Workflow：v1 Replay、v2 Replay/时间跳跃（如有 timer）、Activity retry/heartbeat/cancel、Worker 重启、重复消息、API/Temporal/DB 崩溃窗口与投影对账；
- 安全：跨租户/空间/密级、ID 枚举、下载/预览重新授权、MIME/魔数错配、路径穿越、宏/活动内容、OOXML 解压炸弹、畸形文档、资源超限、预览 XSS/外链、日志/事件泄漏；
- Web：上传/批次/列表/详情/版本/Parse/预览、权限、空/加载/错误/partial/retry、深链接和刷新恢复；
- 迁移：真实 PostgreSQL upgrade/down/up，历史 M0—M2 数据与 v1 history 兼容。

### 16.2 真实 E2E

至少交付以下独立、可复现链路：

1. 文本 PDF → Raw/checksum/scan → v2 Parse → page/block/character Anchor → preview 高亮；
2. 扫描 PDF → 真实扫描检测 → 页级 `OCR_REQUIRED` → 明确 `PARTIAL_FAILED/PARTIAL`；若有真实 OCR Provider，再追加 bbox/置信度 E2E，不能以 Mock 代替；
3. DOCX → 段落/表格 Segment → Anchor/preview；
4. XLSX → sheet/row/column/table-cell Segment → Anchor/preview；
5. Markdown、TXT、CSV 各自的真实 parser 集成用例；
6. 同字节重复、同业务资料新版本替代、reparse 成功、reparse 失败保留旧 active、SourceVersion 失效/越权预览阻断；
7. 批次中 success + partial + failed 混合结果，不回滚成功文件；
8. Worker 停止/恢复、瞬态 Activity 重试、取消、重复 complete/retry/reparse、投影修复与 v1 history Replay。

每条证据记录命令、环境、依赖版本、fixture checksum、期望/实际状态、Workflow/Run/业务 ID 和未执行项。不得将单元 Mock、静态页面或供应商宣传计为真实 E2E。

---

## 17. 阶段交付物

- 真实 Source/Parse 后端、Worker、Web、数据库迁移和 typed SDK；
- Parser/OCR SPI、六类 Parser adapter、统一文档模型、SourceAnchor/preview；
- v1/v2 Workflow 兼容与运行手册；
- 脱敏/合成 parser golden corpus manifest、解析质量/失败/部分成功报告；
- 文件安全与 Parser 隔离报告、依赖/许可证/SBOM/CVE 记录；
- OpenAPI、事件 Schema、SDK、ADR、架构/数据/状态/Workflow baseline、需求追踪、CHANGELOG、PROJECT_STATUS 与 INDEX 更新；
- migration upgrade/down/up、真实 E2E、故障恢复和安全证据。

---

## 18. 最低验收标准

- [ ] M2 v1 Stub 保持可 Replay，M3 v2 真实 Workflow 不把 Stub 结果冒充业务成功；
- [ ] Raw key/checksum/对象 version/条件写成立，同一原始文件不可静默覆盖或跨对象合并；
- [ ] 六类白名单文件具有真实 parser 集成结果，DOCX/XLSX 保留结构；
- [ ] 扫描 PDF 被真实检测并诚实进入 `OCR_REQUIRED/PARTIAL`；只有真实 OCR Provider 才可声明 OCR 完成；
- [ ] initial failure、partial、retry、reparse success/failure/cancel、版本替代/失效均有明确版本、状态、审计与 Outbox；
- [ ] reparse 失败不破坏旧 active 结果，改变 parser/config 不复用旧 ParseJob；
- [ ] paragraph/table/bbox/character/page Anchor 可定位回固定 SourceVersion + ParseJob；失效/重定位不改写历史 Anchor；
- [ ] 真实 MalwareScanner、文件安全、预览净化、跨租户/密级和下载重新授权门禁通过；
- [ ] 真实 PostgreSQL/RustFS/Temporal E2E、Worker 恢复、迁移 down/up、OpenAPI/Event/SDK/前端与全局 CI 通过；
- [ ] 新依赖已锁定并记录用途、许可证、供应链风险和替代方案，无未批准高危漏洞；
- [ ] 无新增 P0 架构、安全、权限、证据、版本或迁移问题，用户已有修改未被覆盖；
- [ ] 所有通过/未通过/未执行声明与真实证据一致。

---

## 19. 需求追踪与验收证据

| 需求 | M3 验收映射 |
|---|---|
| NXW-SOURCE-001 | 资料/版本/Parse/Segment/Anchor/API/UI/安全/真实 E2E |
| NXW-SOURCE-002 | PDF、DOCX、Markdown MVP 上传解析；TXT/CSV/XLSX 为任务书增量 |
| NXW-CLAIM-002 | 仅 SourceAnchor 定位基础，仍为 PARTIAL，不创建 Evidence |
| NXW-NFR-AUD-001 | Source/Parse/parser/config/actor/Workflow 版本追溯增量 |
| NXW-NFR-AVL-002/003 | Parse Worker 恢复、Raw manifest/恢复边界增量，不声称生产 HA/DR |
| NXW-NFR-SEC-001/003 | 文件、密级、扫描、依赖/SBOM 与审计增量 |
| NXW-ARCH-001/002 | Port 隔离、v1 Replay、v2 Workflow 确定性持续门禁 |

最终将已真实验证的 M3 行更新为 VERIFIED/PARTIAL，并保持 M4+ 业务 BASELINED；Parser Stub、扫描检测或 Anchor 基础不得提前关闭 Compile/Evidence/Release 需求。

---

## 20. 禁止事项与停止边界

1. 不得修改 M2 v1 历史 Workflow 语义、已验收迁移或把 `STUB_SUCCEEDED` 映射为解析成功。
2. 不得将 ManagedObject、整篇文本、临时页码、字符串搜索、Mock OCR/Scanner、固定 JSON 或静态 UI 冒充 M3 能力。
3. 不得让 Parser/OCR 直接获得无限网络、宿主文件系统、长期 S3 凭据或数据库权限。
4. 不得绕过权限、密级、审计、幂等、ObjectStoragePort、Parser/OCR Port 或 Temporal。
5. 不得自动合并重复资料、覆盖 Raw/Segment/Anchor、删除失败/审核/历史事实或物理清理已登记 Raw。
6. 不得加入客户、设备、RCA 专用分支或执行 Connector、模型、Compile、Evidence、Review、Release、Query、GridCrew 功能。
7. 不得伪造测试、OCR、恶意文件扫描、性能、许可证、专家、Git 或外部系统证据。
8. 不得覆盖/重置用户修改、自动提交/push 或自行进入 M4。

本次治理校准已完成，用户已明确授权继续 M3 正式实施与实施后独立审查。M3 实施、审查与必要修复完成后必须停止在 M3，未自行进入下一 Milestone。

---

## 21. 实施顺序

1. 再次盘点 git、M2 契约/迁移/Worker 和未提交修改；
2. 形成 M3 implementation plan、依赖/Parser 选择记录和 fixture manifest；
3. 先实现 pure domain、状态、Parser/OCR Port、contracts、OpenAPI/Event/SDK；
4. 新增 `0004` 与 PostgreSQL repository，验证约束/down/up；
5. 实现 SourceUpload/Raw/真实扫描与受控下载；
6. 实现 v2 Workflow/Activity/Parser adapters、结果/Anchor/重定位；
7. 实现 API 和真实 Web 资料中心/preview；
8. 完成单元、架构、契约、集成、Workflow、安全、UI、迁移和真实 E2E；
9. 更新运行手册、质量/安全/解析报告、基线、追踪、CHANGELOG/STATUS；
10. 检查文档链接、生成物漂移、git diff 与用户修改，按下列格式回报并停止。

---

## 22. Codex 最终回报格式

```markdown
# NEXWEAVE M3 执行结果

## 1. 总体结论
- 阶段：通过 / 有条件通过 / 不通过
- 是否满足进入下一阶段条件：是 / 否
- Git 基线：提交哈希 / 未提交及原因

## 2. 实际完成范围
- 按任务书章节逐项说明，区分真实 Parser、扫描检测、真实 OCR 与未实现能力。

## 3. 新增或修改文件
- 文件路径：用途、核心变更、对应需求 ID。

## 4. 领域对象、API、事件、SDK 和 Workflow
- 新增：
- 修改：
- v1/v2 兼容：
- ADR：

## 5. 测试与验证
- 命令、环境、fixture checksum、结果：
- 未执行项及原因：

## 6. 数据库与迁移
- 迁移文件：
- 回滚验证：
- M0—M2 数据兼容性：

## 7. 安全、权限、审计与证据检查
- 文件/Parser/OCR、Raw、preview、Anchor、Secret/日志结论与证据：

## 8. 依赖与供应链
- 新依赖、版本、许可证、SBOM/CVE、替代方案：

## 9. 风险与遗留项
- P0：
- P1：
- P2：

## 10. 需求追踪更新
- VERIFIED / PARTIAL / 未覆盖：

## 11. 停止声明
已停止在 M3，未自行进入下一 Milestone。
```

---

## 23. 交付判定

M3 成功不以文件类型列表、代码量或页面数量判断，而以“不可变 Raw、真实安全扫描、版本化解析、诚实的部分失败/OCR 能力表达、可复现 SourceAnchor、可靠 Workflow、可授权预览和真实跨系统证据”是否同时成立判断。
