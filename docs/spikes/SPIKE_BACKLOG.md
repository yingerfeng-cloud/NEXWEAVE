# Technical Spike Backlog

> M-1 只定义验证计划。Spike 结果必须有可复现命令、环境、数据、指标、失败记录和 ADR 影响，不得以设计推测代替实测。

## SPK-001 Temporal 执行权威

- 问题：Temporal 是否适合作为解析、编译、审核、评测、发布、Pack 安装和回流的唯一可靠执行内核？
- 方法：实现最小无业务 Workflow，验证 Replay、版本升级、时间跳跃、长等待 Signal/Update、Activity 幂等、Worker 重启、取消、补偿和 DB 投影对账。
- 通过：Workflow 无不确定 I/O；重复请求不产生重复业务结果；Worker 重启可恢复；DB 投影可从 Workflow/业务结果修复且不反向推进。
- 输出：测试代码/报告、Workflow ID/错误分类/升级策略、ADR-0004 建议。
- 最晚：M0。

## SPK-002 PostgreSQL + pgvector + Relation 表

- 问题：R1 是否可不依赖 OpenSearch/专用图数据库完成全文、向量、属性和基础关系查询？
- 方法：使用代表性脱敏数据规模，测试 FTS、metadata filter、pgvector、RRF、1—3 跳关系查询、权限过滤和 Release 重建。
- 通过：达到经批准的 R1 p95/吞吐目标；查询只依赖可重建投影；无无法迁移的核心语义。
- 输出：数据集、SQL/索引、基准报告、Provider 契约差距、ADR-0005/0006 建议。
- 最晚：M0 设计，M7 复验。

## SPK-003 数据库与 Markdown/YAML 权威边界

- 问题：结构化属性、Markdown、人工保护区、diff、导入导出和 Release 如何保持可复现？
- 方法：定义 canonical model 与 Markdown/YAML round-trip fixture，测试并发编辑、重编译保护区、导出/回导冲突和历史版本。
- 通过：round-trip 无语义丢失；冲突显式；数据库/Release manifest 是业务权威，Markdown 可重建/交换。
- 输出：canonical schema、diff 策略、fixture、ADR-0007 建议。
- 最晚：M0。

## SPK-004 SourceVersion 与对象存储

- 状态：`PROVIDER_PASS / CI_PENDING`（2026-08-24）；真实 RustFS S3 子集、单节点恢复、逻辑备份和 ARM64 CVE/SBOM 已通过，双架构签名回执等待首次 GitHub main CI，业务扫描 Activity 仍按 M1/M3 边界实现。
- 问题：checksum、对象 key、上传会话、同内容幂等、替代版本、失效和受控下载如何设计？
- 方法：用真实 RustFS/S3 兼容环境验证上传、下载、Range、multipart、失败重试、checksum、同 key 保护、版本控制、预签名 URL、权限、扫描状态、重启恢复和生命周期。
- 通过：Raw 不可静默覆盖；数据库/对象一致；失败可恢复；下载始终重新授权。
- 输出：对象 key 规则、S3 兼容矩阵、状态机、错误/补偿、备份恢复证据、镜像双架构/签名/SBOM/CVE 证据、ADR/数据约束。
- 最晚：M0/M1。

## SPK-005 Parser Provider 与 SourceAnchor

- 问题：PDF、扫描 PDF、DOCX、Markdown、表格如何统一 Block/Segment/Anchor 并定位回原文？
- 方法：建立脱敏 golden corpus，至少覆盖文本 PDF、扫描 PDF、DOCX、Markdown、合并单元格表格；比较 parser/OCR Provider。
- 通过：页/段/字符/表格/bbox 定位可验证；重解析能识别 Anchor stale/relocate；失败/部分成功可版本化。
- 输出：ParserPort、统一文档模型、Anchor schema、准确率/失败报告。
- 最晚：M0 契约，M3 实现。

## SPK-006 Domain Pack 声明与兼容

- 问题：Pack 如何安全声明 Schema、模板、Prompt、规则、评测和迁移？
- 方法：用 equipment-rca 与第二个虚构 Pack 验证安装、依赖、破坏性变更、卸载、回滚、签名和恶意包。
- 通过：不改平台代码/核心表即可安装；任意代码/路径穿越/破坏性变更被阻断；回滚不丢历史知识。
- 输出：JSON/YAML schema、兼容矩阵、迁移 DSL 范围、ADR-0009。
- 最晚：M0/M4。

## SPK-007 Model Gateway 与数据出域

- 问题：chat、structured output、embedding、预算、脱敏、密级、审计和供应商切换如何统一？
- 方法：最小两类 Provider 或一个真实+一个确定性 Provider；验证结构化输出、超时、重试、限额、敏感数据策略和审计。
- 通过：业务代码不暴露厂商响应/SDK；高密策略可阻断；Prompt/Model/成本/错误可追溯；密钥不泄漏。
- 输出：ModelGatewayPort、能力声明、错误语义、数据分类矩阵、ADR-0010。
- 最晚：M0/M5。

## SPK-008 GridCrew Knowledge Pack → Skill

- 问题：Skill/EmployeeRelease 如何固定 NEXWEAVE space/release/policy 并安全查询 Evidence/Graph？
- 方法：双方联合契约 fixture 和 Mock Server，验证身份透传、租户映射、固定版本、超时重试、Webhook 重放、废止和反馈草稿。
- 通过：运行中 Task 不被新 Release 静默改变；越权/草稿访问被阻断；双方审计可用 correlation ID 对账。
- 输出：OpenAPI/事件 schema、映射模型、错误码、ADR-0011。
- 最晚：M0 先冻结语义，M8 联调。

## SPK-009 Python/FastAPI 与企业 Java 适配

- 问题：Python 产品核心能否满足团队能力、性能、合规、可观测性和企业 Java/CUD4.0 集成？
- 方法：构建无业务健康/契约切片，验证类型/生成契约、并发、OTel、依赖治理、容器和 Java API 壳互操作。
- 通过：满足批准的工程基线；企业壳不复制知识内核；可清楚说明运维与人才风险。
- 输出：技术选型报告、ADR-0003/0012。
- 最晚：M0。

## SPK-010 身份、多租户与 RLS

- 问题：OIDC、服务身份、tenant/space ABAC 与 PostgreSQL RLS 如何组合？
- 方法：构造跨租户/空间/对象/密级矩阵，验证应用层、DB 层、后台 Worker 和服务到服务调用。
- 通过：所有越权路径阻断并审计；后台任务不会丢失租户上下文；无前端信任。
- 输出：授权矩阵、Policy contract、RLS 取舍、ADR 建议。
- 最晚：M0/M1。

## 优先顺序

P0：SPK-001、003、005、008、009、010。  
P1：SPK-002、004、006、007。  
所有 Spike 在进入相关编码阶段前需由责任人批准结果；未通过时更新 ADR/OPEN_QUESTIONS，而不是隐藏风险。
