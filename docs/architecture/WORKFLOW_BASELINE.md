# Workflow Baseline

> 执行内核：Temporal（Accepted）。M0 实现独立 Worker 主机和一个无 I/O 的确定性健康 Workflow；以下业务 Workflow 仍是后续阶段冻结的契约，不代表已实现。

## 通用规则

- Workflow ID 使用稳定业务 ID 派生，禁止随机线程 ID 作为业务标识；
- Workflow 代码保持确定性；DB、文件、网络、模型、通知和时钟外部行为仅在 Activity；
- Activity 使用业务幂等键，声明超时、重试、不可重试错误、心跳和取消；
- Temporal 保存执行事实，DB 保存业务对象、决策、结果和查询投影；
- 投影可对账/修复，不得反向成为第二套执行状态机；
- Signal/Update 必须校验调用者权限、业务状态、版本和幂等。

## SourceIngestionWorkflow

- 目标：上传完成后完成校验、扫描、登记、解析准备和状态更新。
- Workflow ID：`source-ingestion/{tenant}/{source_version_id}`。
- 输入/输出：SourceVersion ID、checksum、策略版本 → READY/PARSE job 或稳定失败。
- Activities：读取对象元数据、checksum 校验、恶意文件扫描、创建/更新业务结果、启动解析。
- Updates/Signals：取消、补充元数据、管理员标记误报。
- 可靠性：扫描/存储 I/O 可重试；checksum 不匹配不可重试；取消不删除 Raw。
- 幂等键：SourceVersion ID + policy version。

## KnowledgeCompileWorkflow

- 目标：将固定 SourceVersion + SchemaVersion 编译为可审核候选知识。
- Workflow ID：`compile/{tenant}/{compile_job_id}`。
- 输入/输出：source set、schema、prompt、model、mode → versioned candidates/statistics。
- Activities：segment selection、model structured extraction、entity normalization、relation/claim/evidence candidate、page decision、conflict detection、Lint、persist result。
- Updates/Signals：pause、resume、cancel、retry failed step、补充人工映射。
- 可靠性：步骤级幂等；重复执行不生成重复 Page/Entity；模型安全/预算策略不可绕过。
- 幂等键：CompileJob ID；各 Activity 使用 job+step+input hash。

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

## DomainPackInstallWorkflow

- 目标：校验 Pack、依赖、签名、兼容性并在空间生成新 Schema 配置。
- Workflow ID：`pack-install/{tenant}/{installation_id}`。
- Activities：fetch package、verify checksum/signature、validate manifest、resolve dependencies、impact preview、apply declarations、verify、record installation。
- Updates/Signals：approval、cancel、rollback。
- 可靠性：禁止任意代码；失败/卸载不删除既有知识；升级显式迁移。
- 幂等键：space+pack version+requested config hash。

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

## 待验证

详见 `docs/spikes/SPIKE_BACKLOG.md`：Replay、时间跳跃、版本升级、Worker 恢复、Signal 权限、投影对账、Continue-As-New、长等待和跨 Namespace 策略。
