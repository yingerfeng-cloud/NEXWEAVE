# ADR-0024: M5 Compile、Wiki 与 Model Gateway 实现契约

- Status: Accepted
- Approval basis: 用户于 2026-08-30 明确下发“请执行 M5”；本 ADR 是 M5 编码前强制校准的一部分
- Date: 2026-08-30
- Decision owners: 产品/架构/知识工程负责人
- Related: ADR-0004, ADR-0007, ADR-0008, ADR-0010, ADR-0013—0016, ADR-0020—0023

## Context

M4 已把不可变 `SchemaVersion` 冻结为 R1 唯一语义权威。M5 首次产生真实知识草稿并执行模型调用；若编译输入、稳定身份、页面保护区、模型审计和 Workflow 兼容性未先冻结，重编译可能静默覆盖人工内容、让 Pack/Schema 升级改变历史结果，或把模型文本误当正式知识。

## Decision

### 固定编译输入

- `CompileJob` 创建时固定一个空间内的 `PUBLISHED SchemaVersion`、其 `composition_checksum`、非空 `SourceVersion` 集合及各自 checksum、一个 `PromptVersion` 和一个 `ModelProfile`。运行中不可替换。
- 每个 SourceVersion 必须具有成功或部分成功且仍有效的 active ParseJob；编译只读取该固定 ParseJob 的有效 Segment/Anchor。
- 输入指纹由排序后的固定版本 ID/checksum、编译模式、规范化算法版本和范围组成。相同请求可生成可审计的新 Job，但知识对象使用稳定身份去重，不能产生重复 Entity/Page。

### Model Gateway v1

- 应用只依赖统一 `ModelGatewayPort`，支持结构化生成与 embedding；Provider 响应不进入领域模型。
- Gateway 在调用前执行密级、Provider 出域、最大输入、超时和预算策略；`HIGHLY_RESTRICTED` 永不路由到 externally-hosted Profile。
- 每次调用记录 ModelProfile、PromptVersion、CompileJob/Step、输入/输出 checksum、token/字符计量、耗时、预算和安全错误；不记录凭据或未脱敏原文。
- R1 本地验收 Provider 为确定性、无网络的 `nexweave.local-structured/1`，用于真实可重放流水线和契约验证；外部厂商 Adapter 需独立凭据和部署验收，未配置时不得伪称已调用外部 LLM。

### 候选知识与稳定身份

- Entity 使用 `schema_version_id + type_key + normalized_key` 决定空间内稳定身份；显示名称不是身份。EntityVersion 追加式保存属性、别名、生成 provenance 和状态。
- Relation/Claim/Evidence 均为 M5 候选草稿，不是正式知识；它们固定生成时 SchemaVersion、CompileJob、Prompt/Model 和 SourceAnchor。因果 Relation/Claim 没有可定位 Anchor 时只能进入 lint/人工队列。
- 未知术语、类型或 mapping 只创建 `SemanticChangeProposal`；不得写入当前 SchemaVersion、自动建立 EXACT mapping 或绕过类型约束。
- 歧义映射保留候选和原因，状态为 `NEEDS_MAPPING`；不得以标题、向量相似或模型置信度静默选择。

### Wiki 版本与保护区

- `WikiPage` 是稳定身份，按主 Entity ID 和模板 key 定位；`WikiPageVersion` 是追加式不可覆盖版本。
- 页面规范内容分为 `generated_sections` 与 `protected_sections`。重编译只能替换 AI 生成区；人工编辑通过新版本写入保护区，后续 AI 不得修改。
- Markdown 是交换/展示表示，结构化 JSON 和版本行是数据库权威。页面编辑需要 `If-Match`，并总是创建新版本。
- 双向链接由稳定 Page ID 关联；反向引用、diff、评论和关注均由真实持久化事实驱动。M5 页面只处于草稿/待审状态，不进入 Release。

### Workflow 与回放

- 保留 `nexweave.knowledge-compile.v1` 作为 M2 Kernel Stub 历史；M5 使用 `nexweave.knowledge-compile.v2`。
- v2 Workflow 仅编排确定性步骤与调用 Activities；数据库、模型和对象读取均在可重试 Activity 中。
- 每一步以 `compile_job_id + step_key + input_checksum` 幂等；失败保留完成步骤、调用记录和安全摘要，允许从步骤边界重试。

### 阶段边界

- M5 实现候选 Conflict/Lint 和人工映射队列，但不实现 M6 的正式冲突裁决、ReviewTask/Approval 或高风险职责分离闭环。
- M5 不实现 Release、正式 Query、图投影、GridCrew 消费、自动 RCA 或外部模型供应商部署验收。

## Consequences

M5 能形成可复现、可审计的 Source→Schema→候选知识→Wiki 草稿纵向闭环，同时保持 M6 Review/Evidence 治理与 M7 Release 的独立门禁。新增 Provider、改变稳定身份、允许 AI 编辑保护区、改变 Prompt/Model 锁定或把候选升级为正式知识，均需新 ADR 和兼容迁移。
