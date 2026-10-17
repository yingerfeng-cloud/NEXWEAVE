# ADR-0039 R1 Web 操作与 OIDC 会话闭环

- Status: Accepted for implementation under the explicit R1 remediation authorization.
- Date: 2026-10-17
- Scope: Review F06—F11 / 用户 B 批；不进入 M10，不改写历史验收。

## 决策

1. Web 通过受 A 批共享门禁保护的候选/审核上下文读取服务展示服务端正文、版本、支持/反对证据、原文定位和已执行动作。人工选择策略和候选、填写理由后才起案或执行阶段动作；不以通用 Workflow 批准绕过业务审核。
2. 冲突详情同时展示双方上下文和历史裁决，明确选择保留双方/条件成立/过期/未决/重开。CONDITIONAL 必须给条件，所有裁决必须有非空理由；解除阻断以服务端状态为准，原始对象不静默覆盖。未实现物理合并的 MERGE 不在 Web 中伪装为合并。
3. 问题集明确选择 Schema，支持多题、期望文本/Claim/拒答条件；维护通过追加新版本完成。运行明确选择目标、检索策略与支持的过滤条件；逐题查看实际结果。发布显式选择 Schema、模型/Prompt、问题集和 Claim/Relation/Wiki 版本，不默认全选。正式关系读取复用共享门禁。
4. 空间变化卸载旧页面状态并清除旧空间详情路由；异步队列轮询实际服务端终态。连接器“保存配置”只表示保存，实际同步另行触发/读取结果，不以改名伪装连接验证。
   图谱通过受共享门禁保护的冻结实体列表选择起点，不要求业务用户提前取得数据库 UUID；显示的实体名来自所选 Release。
5. 保持 ADR-0019 的 API Bearer 边界。OIDC Web 使用 Authorization Code + PKCE S256；服务端配置可信授权/Token/JWKS 端点及固定 Web callback，Redis 保存一次性 state/verifier/nonce 与浏览器绑定。服务端兑换并校验 ID token issuer/signature/audience/nonce 及 access token、实际用户身份，再将短期 Bearer 会话返回 Web。Web 清除 callback 参数，仅在 sessionStorage 保存会话，到期/401 清理并回到登录；不索取离线刷新凭据。生产 dev/session 继续关闭。外部 IAM 联调单列，不因替身 IdP 通过而宣布生产验收。
6. kernel/parser 的生产身份配置跟随部署环境，不硬编码 local；worker 不作为 Web 用户签发凭据。新增配置通过既有 Settings / 环境机制，不提交秘密。

## 兼容性和验证

追加 API/可选响应字段，不改变历史 Release、审核动作和已发布迁移；追加 0013 仅拓宽 ReviewCase 既有目标类型约束；不修改历史迁移。
真实 PostgreSQL/路由回归保护权限边界；组件回归验证表单参数/空间切换/终态；真实浏览器从新空间操作。
OIDC 需状态重放/跨浏览器/nonce/签名/到期/生产禁用开发入口的正反控；外部服务缺失记录阻塞并继续独立实现。

规范依据：[OIDC Core 3.1.3.7](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation)、
[RFC 7636](https://www.rfc-editor.org/rfc/rfc7636)、[OAuth 安全 BCP RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html)。
安全复核补充：候选 manifest 的冻结实体名与问题集引用也必须在当前读取权限内；受限候选只返回明确的元数据视图，不泄露快照/说明/诊断正文。
受限/失效评估详情返回 `result_visibility=METADATA_ONLY`，隐藏答案、题目、引用、检索配置与评分；保留执行状态供排障，不能将被隐藏的历史分数视作当前通过。原运行记录和逐题轨迹不改写。

浏览器补充复现：TXT 末尾换行使旧解析器丢失末段或误报空文档。新增 builtin/1.0.1 修复末段边界，保留 1.0.0 的历史算法以支持冻结任务重放；新导入与重新解析默认使用 1.0.1，旧 ParseJob、Anchor 和 Raw 不改写。

Wiki 闭环补充：原发布门禁要求 Wiki 版本已批准，但没有正式批准入口。将 WIKI_PAGE_VERSION 纳入相同 ReviewCase 服务，绑定整个不可变正文/人工保护段，展示对应原文锚点，执行同样阶段角色与高风险职责分离。批准事实来自该版本的 APPROVED ReviewCase，不修改不可变 Wiki 行的 status，也不从 Claim 审核推定整页已经审核。版本内容的编辑仍通过已有 Wiki 版本追加机制，改变后需新案。新增迁移 0013 只扩展目标约束；存在 Wiki 审核历史时回退迁移明确失败，需保留备份并前滚修复，不删除审核历史迁就降级。

发布清单补充：实体的冻结版本必须来自本次明确选择的内容之编译来源，不能因后续无关编译改变当前指针而带入未选工况的来源依赖。Wiki 的来源锚点与主实体显式进入清单；这些是上下文来源，不伪装为已批准 Claim Evidence。纯 Wiki 发布仍须整页人工审核和真实质量门禁。
