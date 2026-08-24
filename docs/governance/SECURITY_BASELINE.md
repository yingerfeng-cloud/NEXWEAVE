# Security Baseline

> M-1 安全与隐私基线；具体控制、算法和供应商由 M0 及后续 Milestone 冻结。

## 1. 信任边界

- 浏览器、上传文件、Prompt、模型输出、Domain Pack、Connector、Webhook、Obsidian 和 GridCrew 请求均视为不可信；
- 服务端执行认证、授权、密级、租户/空间、状态和版本校验；
- 数据库、对象存储、Temporal、Redis、模型和外部系统使用独立最小权限身份；
- 管理面、数据面和外部集成面需分离权限、速率和审计策略。

## 2. 身份与授权

- OIDC 兼容；校验 issuer、audience、signature、expiry、nonce/state 和 token type；
- User 与 ServiceIdentity 分离，凭据独立轮换和撤销；
- RBAC 定义职能，ABAC 约束 tenant、space、object、classification、risk、release 和 action；
- 默认拒绝；跨租户/空间请求在服务端阻断并审计；
- 高风险创建人与最终批准人分离；服务身份不得继承人类超级权限。

## 3. Raw / Draft / Release

- Raw 原始字节不可被 LLM 或编辑 API 覆盖；下载/预览经过权限和水印/导出策略；
- Draft/Review 内容默认不被普通查询、GridCrew 或业务应用读取；
- Release 不可原地修改；发布、废止、回滚、导出和订阅操作审计；
- 缓存、索引和导出按 Release/权限隔离，权限撤销后有可验证失效策略。

## 4. 密级与模型调用

候选级别：PUBLIC、INTERNAL、CONFIDENTIAL、HIGHLY_RESTRICTED。最终名称与策略待批准。

- HIGHLY_RESTRICTED 默认禁止外部模型；
- ModelProfile 声明部署位置、允许密级、数据保留、训练使用、区域和日志策略；
- Prompt/上下文最小化、脱敏，并记录策略版本，不在普通日志保存完整敏感内容；
- 模型密钥仅存 Secret Provider 引用，不进 DB 明文、前端、事件、Trace 或 Git；
- 模型输出是不可信候选，必须经过结构校验、Evidence 与审核。

## 5. 文件与解析安全

- 类型白名单、扩展名/MIME/魔数一致性、大小/页数/解压比限制；
- 防路径穿越、压缩炸弹、宏、脚本、嵌入对象、恶意字体/图像和解析器 RCE；
- 扫描状态为一等状态，M1 Stub 也不得绕过门禁；
- Parser/OCR 隔离资源、超时、网络、文件系统和临时目录；
- 原文预览做内容安全处理，不执行 HTML/JS/外链；
- 失败、部分成功和重新解析保留版本与审计。

## 6. Prompt 注入与可信查询

- 原始资料中的指令仅是数据，不能改变系统策略、工具权限或输出契约；
- 模型/检索层不能自行扩大 tenant/space/release/field 范围；
- Citation 返回前验证 Release、Evidence、SourceAnchor 与权限；
- 证据不足、冲突和反向证据必须可见；禁止伪造引用或输出高风险自动执行指令；
- 外部 URL/Connector 抓取需 SSRF 防护、网络白名单、内容大小和重定向限制。

## 7. Connector 与 GridCrew

- CredentialRef 指向 Secret Provider；密钥不进入日志、DB 明文或前端；
- 出站访问按域名/IP/端口/协议白名单；防 SSRF 和 DNS rebinding；
- Webhook 签名、时间戳、delivery ID、重放窗口和密钥轮换；
- GridCrew 服务令牌限制 audience、tenant mapping、space、release、operation；
- 外部写入只能进入 Source/Draft/Feedback Workflow，不能直接写正式知识。

## 8. Domain Pack 供应链

- 只允许声明式内容，不执行任意代码、宏、远程 include 或绝对路径；
- 校验 checksum、签名、发布者、依赖、平台兼容、许可证、撤销状态和内容大小；
- Prompt/模板/样例视为不可信并进行注入、泄漏和越权测试；
- 安装先在隔离测试空间生成影响预览；卸载/回滚不删除历史知识。

## 9. 审计与可观测性

- 认证、拒绝、上传、下载、导出、模型调用、编译、审核、批准、冲突、评测、发布、回滚、查询、凭据/权限变更全部审计；
- AuditLog 追加式，记录 actor、target、action、decision、reason、policy version、correlation ID 和结果；
- 日志/Trace/Metric 不记录密码、token、Cookie、密钥、完整高密原文或未经批准的 Prompt；
- 时间同步、审计保留、封存、导出和访问权限由安全负责人批准。

## 10. 依赖与许可证

- 锁定直接/传递依赖，生成 SBOM，执行 SCA、secret scan、恶意包/来源检查；
- 记录许可证与通知义务；高危漏洞无批准例外不得发布；
- 基础镜像、Pack、构建产物需 checksum/签名和可追溯来源；
- 禁止来源未知、停止维护或无替代评估的关键依赖。

## 11. 验证基线

至少覆盖：跨租户/空间/对象越权、ID 枚举、权限撤销、路径穿越、恶意文件名、压缩炸弹、解析器超时、Prompt 注入、SSRF、Webhook 重放、凭据泄漏、草稿泄漏、Citation 越权、Pack 路径/签名、发布职责分离和审计完整性。

正式安全联系人、数据分类矩阵、密钥管理产品、漏洞响应 SLA、渗透测试与合规标准仍为开放项。
