# ADR-0021: M3 Source、解析版本与 SourceAnchor 语义

- Status: Accepted
- Date: 2026-08-25
- Approval basis: 用户正式下发 M3 并要求先校准任务书；ADR-0004、ADR-0008、ADR-0013—0018、ADR-0020；已验收 M0—M2 基线
- Decision owners: 产品负责人、架构负责人、安全负责人
- Related: OQ-PARSE-001, NXW-SOURCE-001, NXW-SOURCE-002, NXW-NFR-AUD-001

## Context

M3 首次把 Raw、SourceVersion、ParseJob、DocumentSegment 和 SourceAnchor 从冻结词汇变成业务事实。M2 的 `nexweave.source-ingestion.v1` 只运行 Kernel Stub，成功结果明确不代表扫描或解析成功；直接把它改成业务实现会混淆已验收历史并产生 Temporal Replay 风险。

既有基线已经要求 Raw 不可覆盖、每次解析保留版本、失败/部分成功/重解析可审计，以及历史 Anchor 不原地改写，但尚未统一以下执行语义：重新解析是否覆盖旧结果、重解析失败是否破坏旧的可用解析、扫描件在没有真实 OCR Provider 时如何表述，以及版本替代和 Anchor 重定位如何关联。

## Decision

### 1. Raw、逻辑资料与版本

1. `SourceDocument` 是逻辑资料身份；`SourceVersion` 是不可变 Raw 版本。文件内容、checksum、对象 key 和对象 version ID 在登记后不可修改。
2. 上传开始前分配 `source_document_id`、`source_version_id` 和上传会话；只有服务端重新读取并验证 size、MIME/魔数和 SHA-256 后，才在同一事务登记 SourceVersion、Audit、Outbox 和幂等结果。
3. `SourceDocument` 生命周期使用 `REGISTERED/ACTIVE/ARCHIVED`；归档不删除任何 Raw、解析结果或审计。资料/版本失效使用追加式 `SourceInvalidation` 事实，不复用解析状态，也不物理删除对象。
4. SourceVersion 解析状态保持已接受词汇：`STORED/PARSING/PARTIAL/PARSED/FAILED/SUPERSEDED`。`SUPERSEDED` 只表达同一 SourceDocument 的版本替代关系，不表示字节失效、删除或解析失败。
5. 替代总是创建新的 SourceVersion ID、对象 key 和 checksum，并通过 `supersedes_source_version_id` 形成无环链。旧版本变为 `SUPERSEDED` 后仍可按权限查看和复现；新版本不得继承旧版本的解析结果或 Anchor。
6. checksum 相同只产生幂等命中或疑似重复提示。不同 tenant/space、不同 SourceDocument 或不同业务元数据不得因字节相同而静默合并。
7. `ImportBatch` 只聚合批次内各文件的独立结果，状态为 `CREATED/UPLOADING/PROCESSING/PARTIAL/SUCCEEDED/FAILED/CANCELED`。单项失败或取消不回滚已成功登记的其他 SourceVersion；批次状态不得覆盖单项状态。

### 2. ParseJob、失败、部分成功与重解析

1. 每次解析或重新解析都创建新的 `ParseJob`，绑定固定的 SourceVersion、parser/provider ID 与版本、配置 checksum、文档模型版本、定位器版本，以及可选 OCR provider/config 版本。既有 ParseJob、Segment 和 Anchor 不原地改写。
2. ParseJob 状态为 `CREATED/QUEUED/RUNNING/PARTIAL_FAILED/FAILED/SUCCEEDED/CANCELED`。终态只由 Temporal Workflow 及幂等 Activity 产生；数据库和 UI 不独立推进。
3. `SUCCEEDED` 表示所有强制输出校验通过；`PARTIAL_FAILED` 表示至少一个可用 Segment 已持久化，但存在明确失败单元或能力缺口；`FAILED` 表示没有可作为解析结果使用的输出；`CANCELED` 保留已登记 Raw、步骤事实和诊断。
4. 每个失败单元记录稳定错误码、范围（页/表/工作表/块）、是否可重试和安全的诊断；部分成功不得被展示成完整成功。
5. SourceVersion 保存 `active_parse_job_id` 与 `latest_parse_job_id`。首次成功/部分成功分别把 SourceVersion 置为 `PARSED/PARTIAL` 并设置 active 指针；首次无可用输出失败才置为 `FAILED`。
6. 重新解析创建新 ParseJob 和新 Workflow Run。重解析成功后以强 ETag、审计和 Outbox 原子切换 active 指针；重解析失败或取消只更新 latest 指针，不破坏既有 active 结果或把已 `PARSED/PARTIAL` 的 SourceVersion 回退为 `FAILED`。
7. retry 只重试同一 ParseJob 中可重试的未完成/失败 Activity，保持输入与配置不变；改变 parser、版本、配置、OCR 策略或文档模型必须走 reparse 并创建新 ParseJob。

### 3. M2 Workflow 兼容与 M3 执行权威

1. M2 的 `nexweave.source-ingestion.v1`、三步 Stub 和历史 WorkflowTask/Event 保留用于 Replay 与已验收证据，不得把 `STUB_SUCCEEDED` 翻译为 SourceVersion 或 ParseJob 成功。
2. M3 新业务执行使用 `nexweave.source-ingestion.v2`；Workflow ID 为 `source-ingestion/{tenant_id}/{parse_job_id}`。一个 ParseJob 对应一个稳定 Workflow ID；同一 ParseJob 的技术重试使用相同 ID/Run 语义，reparse 因新 ParseJob 获得新 ID。
3. v2 Workflow 只编排确定性步骤、取消和重试。对象读取、checksum/类型校验、恶意文件扫描、Parser/OCR 调用、结果持久化、预览生成、状态/Audit/Outbox 写入全部位于可重试、可心跳、幂等 Activity。
4. ParseJob 是解析业务结果事实；通用 WorkflowTask/Step/Event 继续作为执行查询投影。二者以 ParseJob ID、Workflow ID 和 Run ID 关联，不合并为同一聚合，也不形成数据库第二状态机。

### 4. Parser/OCR SPI 与统一文档模型

1. application 层定义厂商无关 `ParserPort` 与 `OcrPort`；domain/contracts 不导入解析库、办公套件、Temporal、S3 或厂商 SDK。Provider 只在 Worker adapter 边界注册，并声明支持的 MIME、能力、版本和资源限制。
2. M3 文件白名单为 PDF、DOCX、Markdown、TXT、CSV 和 XLSX。旧二进制 DOC/XLS、带宏 DOCM/XLSM、压缩包、URL、网页抓取、图片和音视频不是 M3 导入类型；不得仅按扩展名放行。
3. Parser 输出统一的有序 Block/Segment，至少区分 heading、paragraph、list、table、table cell、image/figure reference 和 page boundary；每个 Segment 绑定 SourceVersion、ParseJob、顺序、规范化文本 checksum、结构路径和适用定位器。解析结果是 Raw 的可重建派生物，不是正式知识或 Evidence。
4. OCR 是独立能力。M3 必须真实识别扫描型 PDF/无文本页并给出 `OCR_REQUIRED` 失败单元；没有已批准且真实运行的 OCR Provider 时，允许形成带可用元数据/页面边界的 `PARTIAL_FAILED`，但不得声称 OCR 或全文解析成功。Stub/固定文本不能作为扫描 PDF OCR 验收证据。

### 5. SourceAnchor 与重定位

1. SourceAnchor 继续遵守 ADR-0014，并在 M3 增加 `parse_job_id`，从而固定产生定位器的解析版本。必填绑定为 source version、Raw checksum、parse job、locator version 和 excerpt hash。
2. M3 使用现有 locator v1 类型：page、block、character range、table cell 和 normalized top-left bounding box。段落通过稳定 block ID 表达；不得以临时页码或全文字符串搜索作为唯一定位。
3. Anchor 状态只使用 `VALID/STALE/UNRESOLVED/REVOKED`。`RELOCATED` 是 `relocated_from_anchor_id` 关系，不是状态；不得使用未接受的 `INVALID` 状态。
4. reparse 后先运行失效检测：仍可验证的旧 Anchor 保持 `VALID`；无法在原解析结果中验证的标记 `STALE`；重定位成功创建新 Anchor 并链接旧 Anchor；无法重定位创建/保留 `UNRESOLVED` 事实。历史 Anchor 不原地改写为新的 locator。
5. SourceVersion 被失效或访问被撤销时，相关 Anchor 进入 `REVOKED`；历史引用事实保留，但内容展示和下载仍需重新授权。

### 6. 预览、安全与可观测性

1. 原文预览和 Anchor 高亮必须经过 tenant、space、SourceVersion、密级和状态授权；预览是经过安全处理的派生物，不执行 HTML/JS、宏、外链、嵌入对象或活动内容。
2. Parser/OCR Activity 的可信协调器只负责 DB/RustFS/ClamAV/Temporal I/O；实际第三方文档解析运行在单独的无凭据 `parser-sandbox` 容器。该容器仅连接专用 internal IPC 网络，不连接 PostgreSQL、RustFS、ClamAV 或 Temporal 网络，并采用只读根文件系统、独立 tmpfs、非 root、cap-drop、no-new-privileges、CPU/内存/PID/时间/页数/解压比限制。临时文件按受控策略清理，日志、事件、Trace 和错误不记录 Raw 正文或敏感摘录。
3. 文件类型不符、checksum 不匹配、恶意内容、资源上限超限和策略拒绝为不可原样重试错误；瞬态对象存储/Worker 故障可按同一 Activity 幂等键重试。

## Consequences

- 失败、部分成功、技术 retry、配置变化 reparse 和文件替代成为不同且可审计的动作，不会覆盖旧结果。
- M2 Stub 历史与 M3 业务 Workflow 分离，避免把内核验证冒充业务完成或破坏 Replay。
- 扫描 PDF 在没有真实 OCR Provider 时诚实停在 `OCR_REQUIRED/PARTIAL_FAILED`；后续引入 OCR 只需新增 Provider/配置与 ParseJob，不改变 Raw 或 Anchor 历史。
- SourceAnchor 固定 Raw 与解析版本，后续 Evidence、Release 和 Citation 可以复现原始定位。

## Compatibility and migration

- M3 只能新增 `0004_m3_source_parsing`（最终文件名可更具体）及后续 additive revision，不修改 `0001`—`0003`。
- SourceAnchor v1 以新增可选兼容字段过渡；M3 新建 Anchor 必须填写 `parse_job_id`。改变坐标或规范化语义需提升 locator version 并提供转换/失效报告。
- `nexweave.source-ingestion.v1` 保持可 Replay；v2 新 Worker 发布前必须同时通过 v1 历史 Replay 与 v2 Workflow 测试。停止 v1 注册需单独的历史保留/退役证据。
- 公共 API/事件/SDK 只做 `/api/v1` additive 扩展；删除、改义或收紧已公开枚举仍按 ADR-0015 执行兼容窗口。

## Validation

- 同字节幂等、疑似重复不自动合并、条件写与 SourceVersion 替代链；
- initial parse、partial parse、retry、reparse success/failure/cancel 及 active/latest 指针行为；
- v1 Replay、v2 Worker 重启、Activity 重试/心跳/取消、投影对账；
- 文本 PDF、DOCX、Markdown、TXT、CSV、XLSX 的真实解析；扫描 PDF 的真实扫描检测与 `OCR_REQUIRED`，只有真实 OCR Provider 才可声明 OCR 通过；
- page/block/character/table-cell/bbox Anchor 回显、失效检测、重定位与越权阻断；
- MIME/魔数、宏/活动内容、OOXML 解压比、资源上限、预览净化、日志/事件敏感信息检查；
- 真实 PostgreSQL、RustFS、Temporal 的 migration upgrade/down/up 与 Source→Parse→Preview E2E。
