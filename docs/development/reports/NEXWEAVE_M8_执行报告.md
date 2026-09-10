# NEXWEAVE M8 执行报告

## 结论

用户于 2026-08-31 正式验收 M8。验收范围为受控只读 Connector、Obsidian Markdown 草稿交换及内置 Wiki 双向链接导航图谱。GridCrew 尚处规划期，依用户明确指令延期，不属于本次验收范围；M9 未获下发。

## 实际完成范围

- Connector 采用非秘密 `CredentialRef`、显式出站 allowlist 与默认拒绝策略；同步仅写入可追溯的 Raw、SourceVersion 和既有 M3 解析链路。
- Obsidian 交换使用 YAML frontmatter 中的稳定页面标识、基线版本与校验和；回导仅产生草稿或冲突，不覆盖 Release、Evidence、权限、密级或稳定标识。
- 内置 Wiki 图谱从平台 Wiki 页面链接及反向引用生成受限的导航投影；与 M7 的固定 Release 关系图保持独立语义，但可在同一入口切换。
- 图谱 Web 界面提供模板着色、搜索与筛选、2D 拖拽平移/滚轮缩放、关联高亮、局部聚焦和 Wiki 页面跳转。

## 验证与部署

- M8 定向契约/API/前端验证、前端格式化、lint、类型检查和生产构建通过；Web 测试共 18 项通过。
- 本地 API 部署已重建并健康就绪；additive `0009_m8_connector_obsidian` 已成功升级。
- API 就绪检查确认 PostgreSQL、Redis、对象存储与 Temporal 可用；Wiki 图谱端点已载入 OpenAPI。

## 安全、证据与迁移

- 没有修改历史迁移；`0009` 为可追踪的追加迁移。
- Connector 不接受隐式网络目标或秘密明文；Obsidian 回导不具备发布或证据写入权限。
- 图谱读取受 `page.read`、租户/空间隔离、深度和节点上限保护，不将本地 Obsidian Vault 作为权威数据源。

## 遗留风险与停止声明

- 生产部署仍需外部 Secret Provider、OIDC、逐目标网络审批及真实环境端到端验证。
- GridCrew 的 Skill 绑定、Release 查询、证据读取、关系遍历和发布事件消费均未实现，待对端可联调并由用户另行下发。
- 本报告不授权 M9；实现停止在已验收的 M8 边界。
