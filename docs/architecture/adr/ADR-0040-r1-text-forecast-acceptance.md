# ADR-0040 R1 文本与预测能力的可验收边界

- Status: Accepted for implementation under the explicit R1 remediation authorization.
- Date: 2026-10-17
- Scope: Review F04/F05/F12，用户 C 批；保持 R1、不进入 M10。

1. `nexweave.local` 仅开发/测试使用，逐条返回原文与锚点，不因 Schema 声明关系就连接首尾实体。规则关系只接受原文中明确的端点、方向与肯定关系词；否定、列举、推测不产生肯定关系。任何 Provider 仍只产候选，必须人工审核。
2. Model Gateway 增加兼容 HTTP chat-completions/embeddings 适配，使用已存在 HTTPX；端点来自服务端配置，禁止凭模型配置重定向任意地址，TLS/超时/响应预算/密级/SecretRef 均服务端检查。固定 profile/config revision、实际返回模型、请求ID及输入输出校验和可追溯；没有模型/凭据/兼容响应明确失败，不回退到规则或哈希。
3. 新增0014给可重建搜索投影追加真实向量JSON/配置指纹及调用审计，旧vector(16)与历史Release保留但不再用于语义检索。真正SEMANTIC/HYBRID要求明确embedding profile且维度/指纹一致；缺失时报不可用。KEYWORD/ATTRIBUTE独立可运行，明确标注词面检索与原文摘录，不能冒充模型语义问答。发布明确冻结检索配置，Query/Evaluation继续复用同一执行管线和当前证据门禁。
4. 词面检索支持自然问句停用词、Unicode中文片段、Schema术语/别名及实体编号，限定对象一致性，避免“未知对象+共同属性词”误答。独立基准分别报告召回/回答/引用/拒答；保留B失败原题，不能换题/降门槛。真实模型和领域准确率只有实际模型及独立数据运行后才能宣布。
5. ForecastProfile 总协变量最多8，与Binding总列9一致；继续冻结窗口/单位/输入、成功幂等与取消终态。Chronos计算放在可终止子进程，取消后单独验证任务中断、数据库无制品、对象存储暂存清理；不把一类通过等同全部通过。硬崩溃窗口未演练必须记录。
6. 固定Chronos权重与运行版本，提供时间切分、滚动起点、持久值基线及分位损失/覆盖率回测入口；有本地模型和数据即运行。合成数据只证明工程可执行，条件预测不解释为因果、故障概率、优化或自动执行。
7. 真实Web批准角色暴露了租户管理配置读取403阻断发布列表的问题。增加空间授权的执行配置选择接口，只投影模型/Prompt标识、版本和公开能力字段，不暴露凭据引用、Prompt正文或其他空间配置。编译/发布业务页使用该接口；租户管理API维持原权限。配置不可用不得掩盖已经有权读取的发布历史与待批准候选。
8. 来源失效的真实基准暴露了评估准入拒绝前先创建WorkflowTask的问题。共用套件/目标准入检查在任务创建前执行，并在创建EvaluationRun时重检；两次检查之间失效以API_ADMISSION事件记录FAILED，Temporal run_id保持空，不冒充已执行的工作流。运行中的来源失效仍由共享Query/Evaluation证据检查产生真实拒答。
9. 最终停机演练证实早到终审Update被Temporal以RUNNING状态拒绝后，其固定Update ID永久返回缓存失败；队首break同时饿死其他审核。新增0015仅追加持久重试到期时间/索引。逐条失败隔离并有界退避；终审投递先检查匹配的真实完成结果/WAITING步骤，再使用与投递记录及持久尝试次数绑定的Update ID。失败尝试可换ID，事务未提交的同次尝试保持幂等；审批事实仍只有原DB最终决定，不能重写历史、伪造完成或静默丢弃毒化记录。HumanReview v2历史定义不变。
10. 模型配置可用性与实际输入密级分开校验：高权限人员提交INTERNAL内容不应因人员clearance较高而被拒绝；所有真实调用仍按内容密级检查。embedding配置指纹包含非秘密的服务端端点/外部托管策略/凭据引用，端点变化不能继续复用旧向量。凭据值不入指纹或审计；供应方实际权重仍需版本与现场验证。
11. 正式镜像门禁还要求真实文本/embedding的20题合成基准，100%阈值保持不变。缺少模型配置/凭据明确CONFIGURATION_BLOCKED并失败，既不跳过也不以本地规则替代；该技术门禁仍不能冒充工业或专家验收。外部服务配置仅使用现有Model Gateway环境与ModelProfile机制，公开型号/revision配置与秘密分离。

接口依据：[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat) 与 [embedding API](https://developers.openai.com/api/reference/resources/embeddings/methods/create)。仅借用明确协议，不假定账号权限、模型可用或已经产生真实调用。
