# Workflow Baseline

> 执行内核：Temporal（Accepted）。M2 七类 v1 Kernel Stub、M3 SourceIngestion v2、M4 DomainPackInstall v2 和 M5 KnowledgeCompile v2 已正式验收。ADR-0024 的 M5 Activities 已通过本地真实链路技术验收。

## M2 运行拓扑与公共状态

- Namespace：`nexweave-dev`，开发保留期 7 天；生产 Namespace/保留期由部署配置管理；
- Workflow Task Queue：`nexweave-m2-workflows`；Activity Task Queue：`nexweave-m2-activities`；
- Worker：`worker-kernel`，非 root 容器，两个队列各自由 Worker poll；
- 任务状态：`CREATED/STARTING/RUNNING/PAUSED/WAITING/WAITING_INPUT/CANCELLING/COMPENSATING/CANCELLED/SUCCEEDED/FAILED/TIMED_OUT/REJECTED`；
- 控制命令：`PAUSE/RESUME/CANCEL/CLAIM/REQUEST_INPUT/PROVIDE_INPUT/APPROVE/REJECT/RETRY`，由服务端权限、状态、ETag 与幂等键共同校验；
- Temporal 是执行权威；PostgreSQL 是 Task/Step/Event 查询投影，带 projection revision、同步标志与对账修复入口。

## 通用规则

- Workflow ID 使用稳定业务 ID 派生，禁止随机线程 ID 作为业务标识；
- Workflow 代码保持确定性；DB、文件、网络、模型、通知和时钟外部行为仅在 Activity；
- Activity 使用业务幂等键，声明超时、重试、不可重试错误、心跳和取消；
- Temporal 保存执行事实，DB 保存业务对象、决策、结果和查询投影；
- 投影可对账/修复，不得反向成为第二套执行状态机；
- Signal/Update 必须校验调用者权限、业务状态、版本和幂等。
- Activity 采用 15 秒 start-to-close、45 秒 schedule-to-close、5 秒 heartbeat、最多 3 次指数重试的 M2 内核默认；策略错误标记为不可重试；
- 需要批准的内核等待 300 秒后记录 `APPROVAL_TIMEOUT_ESCALATED`，但仍等待授权人工决定。该值只验证 durable timer/升级机制，不决定 M6 业务 SLA；
- 取消按已完成步骤逆序执行补偿并保留审计/日志；重复 Update 返回原命令结果；FAILED/TIMED_OUT 可启动同一稳定 Workflow ID 的新 Run。

## SourceIngestionWorkflow

### M2 v1 已实现边界

- `nexweave.source-ingestion.v1` 使用三步 Kernel Stub，只验证可靠执行、控制、投影与恢复；`STUB_SUCCEEDED` 不创建 SourceVersion、ParseJob、Segment 或 Anchor。
- v1 Workflow/历史必须保留注册与 Replay，不能通过修改 Activity 含义升级为 M3 业务成功。

### M3 v2 已实现并正式验收边界

- 目标：固定 ParseJob 输入后完成 Raw 校验、安全扫描、Parser/OCR 能力选择、版本化解析、Segment/Anchor 持久化、重定位与 active/latest 指针更新。
- Workflow type：`nexweave.source-ingestion.v2`；Workflow ID：`source-ingestion/{tenant}/{parse_job_id}`。
- 输入：ParseJob、SourceVersion/checksum、parser/config/document-model/locator 版本与策略引用；输出为版本化 ParseJob 结果或稳定失败/partial，不输出知识/Evidence。
- Activities：Raw metadata/checksum/type、恶意文件扫描、Parser/OCR、result validation、Segment/Anchor/failure-unit、reconciliation、状态/Audit/Outbox。
- retry 保持同 ParseJob 与配置；reparse 创建新 ParseJob/Workflow。已有 active 结果时 reparse 失败不回退 SourceVersion。
- 扫描 PDF 无真实 OCR Provider 时记录页级 `OCR_REQUIRED`，可为 `PARTIAL_FAILED/PARTIAL`；Mock 不能作为 OCR 验收。
- 所有 I/O 位于可重试、可心跳、幂等 Activity；取消不删除 Raw 或历史结果。

## KnowledgeCompileWorkflow

### M2 v1 保留边界

- `nexweave.knowledge-compile.v1` 继续保留 Kernel Stub 注册和历史 Replay；其 `STUB_SUCCEEDED` 不创建知识对象、Evidence 或 Wiki 页面。

### M5 v2 已实现并正式验收边界

- 目标：将固定 SourceVersion/checksum/ParseJob + PUBLISHED SchemaVersion/composition checksum + PromptVersion + ModelProfile 编译为可审核候选知识和版本化 Wiki 草稿。
- Workflow type：`nexweave.knowledge-compile.v2`；Workflow ID：`compile/{tenant}/{compile_job_id}`。
- Workflow 输入只携带 CompileJob/actor/trace 固定引用；上下文装配、segment selection、Model Gateway 调用、结构化校验、稳定 Entity/Page 归一化、Relation/Claim/Evidence/Conflict/Lint/Proposal 和持久化均位于可重试 Activity。
- v2 本阶段暴露只读状态查询，不暴露业务 pause/resume/cancel Update；失败/取消后重新执行必须创建新的 `RECOMPILE` CompileJob，旧任务和调用审计不可覆盖。
- Activity 使用 CompileJob + step + input checksum 幂等；相同稳定身份复用 Entity/Page，内容 checksum 未变化不制造重复版本。
- 模型分类、外发、预算和结构化输出策略在 Model Gateway/可信 Activity 边界执行；Workflow 不能绕过。外部 Provider 不可用时明确失败，不以本地规则结果冒充外部模型回执。

## HumanReviewWorkflow

- 目标：分派、领取、补充资料、修改、驳回、复核、批准与超时升级。
- Workflow ID：`review/{tenant}/{review_task_id}`。
- 输入/输出：固定待审对象版本、风险/策略 → ReviewAction/Approval/最终决定。
- Activities：创建投影、解析权限策略、通知、保存不可变动作、生成新草稿版本、升级。
- Updates/Signals：claim、submit action、request input、provide input、reassign、approve/reject、cancel。
- 可靠性：长时间等待使用 durable timer；同一高风险对象创建人与最终批准人分离。
- 幂等键：ReviewTask ID + client action ID。

## QualityEvaluationWorkflow

- 目标：对固定目标运行 Lint、标准问题集和回归评测。
- Workflow ID：`evaluation/{tenant}/{evaluation_run_id}`。
- 输入/输出：suite version、target/release candidate、model/prompt/retrieval config → metrics/errors/gate result。
- Activities：materialize target、run deterministic lint、execute question cases、aggregate metrics、store report。
- Updates/Signals：cancel；不允许运行中替换 suite/config。
- 可靠性：题目级幂等和并发限制；失败与不可回答区分。
- 幂等键：suite+target+config hash。

## KnowledgeReleaseWorkflow

- 目标：验证、审批、固化、构建投影、切换指针和通知订阅者。
- Workflow ID：`release/{tenant}/{release_candidate_id}`。
- 输入/输出：candidate manifest、policy → immutable Release 或失败/拒绝。
- Activities：validate evidence/schema/conflicts/evaluation、request approval、freeze manifest、build projections、verify、switch pointer、publish event、compensate pointer。
- Updates/Signals：approval decision、cancel before freeze、retry deployment；冻结后不得修改 manifest。
- 可靠性：发布失败不产生半可见 Release；回滚切换指针，不修改历史。
- 幂等键：candidate manifest hash + target channel。

M7 实现为 `nexweave.knowledge-release.v2`：Workflow 先调用验证 Activity，门禁通过后以 durable wait 等待独立 Publisher 的审计批准，再调用发布 Activity；数据库、Model Gateway、投影与事件 I/O 均不进入 Workflow 定义。发布事务一次性固化 Release/Items/投影/Pointer/Outbox，失败不产生半可见版本。

## QualityEvaluationWorkflow

- M7 实现为 `nexweave.quality-evaluation.v2`，固定 EvaluationRun/Suite/target/strategy/config 引用；逐题结果、问题级错误、指标和门禁由可重试 Activity 原子保存。
- 相同 Suite/目标可使用不同 Model/Prompt/检索策略形成独立 Run 供 A/B 比较，不覆盖既有结果。
- Workflow 只编排引用和结果，评测读取与数据库写入都位于 Activity。

## DomainPackInstallWorkflow

- M2 `nexweave.domain-pack-install.v1` 保持 Kernel Stub 和历史 Replay；M4 业务实现使用 `nexweave.domain-pack-install.v2`，不得修改 v1 Activity 含义来冒充升级。
- 目标：校验 Pack、依赖、签名与语义兼容，确定性组合声明并在空间生成新的 DRAFT SchemaVersion 和 SchemaCompositionReport。
- Workflow type：`nexweave.domain-pack-install.v2`；Workflow ID 由 tenant + install/upgrade/disable/rollback business key 稳定派生，Run ID 单独记录。
- 输入固定：Installation ID、actor/trace 与 Activity queue 引用；Installation 业务行已固定 tenant/space、精确 PackVersion、SchemaDefinition、目标语义版本和操作，Workflow 不携带制品正文。
- Activities：单一幂等业务 Activity 读取已固定 Installation，完成签名/撤销复核、精确依赖 DAG、规范化组合、冲突/影响、DRAFT/report 和 audit/outbox 原子持久化；独立失败 Activity 记录终态和脱敏错误审计。
- 控制：M4 v2 暴露只读 query；升级、禁用和回滚由授权版本化 API 创建新的 control Installation/Workflow，不通过 Signal 改写运行中输入。安装/发布职责分离由 Schema publish API 执行。
- 确定性：Workflow 只编排固定引用和结果；制品读取、签名、依赖解析、持久化和影响扫描均在幂等 Activity。相同规范化输入必须产生相同 composition checksum；安装时间、数据库返回顺序和 Worker 调度不能影响结果。
- 权威边界：安装成功不等于 Schema 发布；发布是独立授权动作。禁止后安装覆盖先安装；冲突、循环、歧义 EXACT mapping 和破坏性变化必须阻断。
- 可靠性：禁止任意代码；失败/禁用/卸载不删除既有 Schema、知识、报告或 Release；升级显式迁移并生成新 SchemaVersion；回滚恢复先前安装/Schema 指针。
- 幂等键：调用者提供的 command key + 服务端 canonical request hash；业务 key 固定 operation/PackVersion/SchemaDefinition/semantic version。

## GridCrewFeedbackIngestionWorkflow

- 目标：接收 GridCrew 的反馈/案例草稿并转为受控 Source/Draft，而非正式知识。
- Workflow ID：`gridcrew-feedback/{tenant}/{external_feedback_id}`。
- Activities：authenticate/authorize context、validate signature/schema、map tenant/space/release、dedupe、create intake Source/Draft、notify reviewer、write cross-audit receipt。
- Updates/Signals：补充上下文、撤回、拒绝。
- 可靠性：GridCrew 重试返回同一 intake；越权或过期 release context 拒绝。
- 幂等键：GridCrew tenant + external feedback ID。

## 补偿与取消边界

- Raw 上传完成后取消不物理删除 SourceVersion；按状态失效/归档。
- Compile 取消保留已完成步骤审计，候选不自动进入审核。
- Review 取消不删除动作历史。
- Release manifest 固化前可取消；固化/发布后通过废止或新 Release 修正。
- Pack 回滚禁用安装并恢复服务指针/配置，不删除历史知识。

## M2 验证边界

- 已验证：七类真实运行、Activity 首次瞬态失败与重试、Update 幂等、人工批准、暂停/继续、取消/逆序补偿、Worker 重启恢复、投影损坏对账修复、历史 Replay；
- 已关闭条件项：官方 Temporal Python SDK time-skipping 测试已于 2026-08-25 在本地及 GitHub Actions run `32808198635` 独立门禁通过；
- M7 补充验证：QualityEvaluation v2、KnowledgeRelease v2 的真实 Temporal 新历史、独立批准等待和发布恢复已通过隔离 E2E；归档生产历史与专门的进程崩溃窗口演练仍作为后续部署风险。
- 后续：Continue-As-New、大规模历史、生产 Namespace 保留/升级与多集群灾备在对应 Milestone/部署环境验证。
