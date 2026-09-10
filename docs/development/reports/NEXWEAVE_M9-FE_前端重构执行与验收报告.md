# NEXWEAVE M9-FE 前端重构执行与验收报告

> 2026-09-07 更新：本文记录 2026-09-01—02 的初轮交付，不再作为当前 UX/UI System Refactor 的最终判定。当前权威报告为 `FRONTEND_REFACTOR_REPORT.md`，审查与设计系统分别见 `docs/design/FRONTEND_UI_AUDIT.md`、`docs/design/FRONTEND_DESIGN_SYSTEM.md`。新报告按任务书使用 PASS/PARTIAL/FAIL，并明确保留未完成深化项；不得沿用本文“P1 清零/未完成项为无”的旧结论。

> 执行日期：2026-09-01—2026-09-02  
> 范围：R1 / M9 补充前端整治  
> 判定：本地技术验收通过；待用户正式验收  
> 停止边界：M9-FE，不构成 M9 业务验收，不授权 M10

## 1. 总体结论

- 阶段：通过。
- 高保真原型对齐：完成。登录与 17 个受保护路由使用统一深黑、紫、青、荧光绿知识操作系统语言。
- 功能回归：通过。真实 API、权限、错误、空间恢复、URL 深链接和 History 语义保持；未引入原型 Mock。
- 补充体验巡检：2026-09-02 根据真实 8080 页面复查，修复移动端导航入口不可见、移动快速导航不可稳定打开、裸按钮触控尺寸不足、长密级指标裁切/不雅断行、图谱/标签页按钮越界和浏览器标题仍显示 M0 的问题。
- Git 基线：未提交。用户未授权 commit、push 或远程 PR；已有未提交 M3—M9 工作未被重置、覆盖或删除。

## 2. 实际完成范围

### FE-0

- 版本化冻结页面→原型→API→关键状态矩阵、六类界面模式、设计 token、组件契约、依赖策略、迁移批次和停止点。
- 明确 Global Search 在本阶段是可达页面快速导航，不冒充知识检索；知识查询仍走 Ask NEXWEAVE 固定 Release API。

### FE-1

- 建立 `tokens.css` 唯一颜色权威和 foundation/shell/components/feature 分层样式。
- 新建 AppShell、分组导航、空间切换、Topbar、真实快速导航、身份状态及共享页面/面板/指标/表格/状态组件。
- 拆出登录页和总览页，保留会话、空间、权限与退出流程。

### FE-2

- 以总览、资料中心、Wiki、Schema/双图谱作为样板页，在三类视口与真实 API 状态下完成渲染检查。
- Wiki 图谱动态颜色收敛为受控的 8 色可视化 token。

### FE-3

- 迁移登录以及 `/overview`、`/spaces`、`/sources`、`/tasks`、`/compile`、`/wiki`、`/schemas`、`/domain-packs`、`/claims`、`/graph`、`/conflicts`、`/reviews`、`/quality`、`/releases`、`/ask`、`/integrations`、`/admin`。
- 将既有真实任务中心纳入 `/tasks`；新深链接为 `/tasks/:id`，兼容历史 `/compile/:id`。
- 路由状态包含 pathname 与 query，修复 `/graph` ↔ `/graph?view=release` 同路径切换；Wiki 选择固化为 `?page=`；任务详情前进/后退恢复使用显式目标 ID。

### FE-4

- `styles.css` 从单文件样式主体改为 8 个分层入口；原 915 行旧覆盖层收敛为 381 行业务结构文件。
- 删除旧 Shell、Topbar、Metric、Panel、Tabs、Login 等与新设计系统竞争的重复权威；最终 CSS 产物由 53.19 kB 降至 44.09 kB。
- 将知识空间和平台管理从 `App.tsx` 拆为 `SpacesPage.tsx`、`AdminPage.tsx`；入口文件仅保留会话、数据和路由编排职责。
- CSS 颜色扫描确认除 `tokens.css` 外无十六进制或 RGB 硬编码；未使用 `any`、关闭规则、远程字体/图片/CDN。

### FE-5

- 独立审查发现并修复：移动审核列表长文本、集成旧截图、graph query 不重渲染、Wiki/Task History 恢复、产品内 M9-FE 标签、旧新 CSS 双重权威、业务样式泄漏和 `App.tsx` 页面职责过载。
- 进一步移除各业务页 M4—M8 实施里程碑标签，改为稳定产品语义；登录页仅保留真实 `LOCAL DEVELOPMENT` 环境提示。
- 修复后重新执行自动门禁、真实浏览器路由/History、三视口全路由截图、横向溢出与干净控制台复核。
- 2026-09-02 补充巡检修复：移动端主导航从横向长滚动改为当前页选择器；快速导航增加真实移动触发按钮；统一 `inline-form`/`m7-form`/错误条/标题按钮触控尺寸；长指标值进入紧凑态；Wiki 图谱节点增加透明命中圈；移动 Tabs 改为两列可见；容器 `web` 已再次重建替换。

## 3. 设计系统与主要决策

- tokens：深黑多层背景；紫/青/荧光绿品牌色；成功/警告/错误/信息独立语义；4px 网格；统一圆角、阴影、层级、动效。
- 组件：AppShell、PageHeader、Panel、Metric、DataTable、StatusPill、Loading/Empty/Error/PermissionDenied。
- 布局：248px 桌面侧栏、64px 顶栏、最大 1500px 内容；工作台、列表详情和图谱使用 `minmax(0, 1fr)`。
- 响应式：1024px 收紧；760px 以下侧栏转顶部区域，主导航由当前页选择器承载，快速导航由按钮展开为输入框，内容单列。
- 可访问性：原生控件、2px `focus-visible`、状态不只依赖颜色、长内容换行、`prefers-reduced-motion` 禁用非必要动画。
- 有意偏离：见 `docs/design/NEXWEAVE_M9-FE_VISUAL_DEVIATIONS.md`。

## 4. 新增或修改文件

### 代码

- `apps/web/src/design-system/AppShell.tsx`：统一 Shell、导航、空间、身份和快速导航。
- `apps/web/src/design-system/ui.tsx`：共享页面、面板、指标、表格和真实状态组件；长指标值自动进入紧凑态。
- `apps/web/src/LoginPage.tsx`、`OverviewPage.tsx`：从路由编排拆出的登录与总览。
- `apps/web/src/App.tsx`：会话、数据、17 路由编排、完整 location key、真实任务入口与图谱/Wiki URL 恢复。
- `apps/web/src/SpacesPage.tsx`、`AdminPage.tsx`：从入口文件拆出的知识空间与平台管理页面。
- `apps/web/src/TaskCenter.tsx`：共享组件、`/tasks/:id`、空 ID 清除和 History 恢复。
- `apps/web/src/WikiWorkbench.tsx`：Wiki 选择写入刷新可恢复 URL。
- `apps/web/src/SourceCenter.tsx`、`IntegrationCenter.tsx`：复用共享组件和统一页面头。
- `apps/web/src/WikiLinkGraph.tsx`：受控图谱色板。
- `apps/web/index.html`：浏览器标题和描述从 M0 工程壳改为产品级本地前端标题。
- `apps/web/src/App.test.tsx`：17 路由、快速导航、graph query、Wiki page URL、Task History 回归。
- `apps/web/src/styles.css` 与 `apps/web/src/styles/*.css`：token/foundation/core/shell/component/source/knowledge/feature 分层。
- `SchemaStudio.tsx`、`M7Knowledge.tsx`、`CompileCenter.tsx`、`ReviewCenter.tsx`、`PackCenter.tsx`：移除开发里程碑标签，保留产品语义。

### 文档与证据

- `docs/design/NEXWEAVE_FRONTEND_DESIGN_SYSTEM_BASELINE.md`。
- `docs/design/NEXWEAVE_M9-FE_VISUAL_DEVIATIONS.md`。
- `docs/development/evidence/m9-fe/baseline/`：7 张原型/旧实现基线。
- `docs/development/evidence/m9-fe/final/`：54 张最终截图（登录 + 17 路由 × 3 视口）。
- 本报告、M9-FE 任务书、`AGENTS.md`、`OPEN_QUESTIONS.md`、`PROJECT_STATUS.md`、`CHANGELOG.md`、`docs/INDEX.md` 和需求追踪矩阵。

## 5. 页面迁移结果

- 已迁移路由：登录与全部 17 个受保护主路由。
- 未迁移路由：无。
- 未实现原型元素：固定 KPI、假资料、假连接、假 Release、模拟问答、静态成功动作；这些不是真实契约，按任务书禁止进入产品。

## 6. 测试与视觉验证

### 自动化

- `npm run format:check`：通过。
- `npm run lint`：通过，0 warning。
- `npm run typecheck`：通过。
- `npm test -- --run`：6 个文件、22 项测试全部通过；基线为 18 项。
- `npm run build`：通过，46 modules；CSS 45.13 kB（gzip 9.03 kB），JS 298.30 kB（gzip 91.48 kB）。
- `git diff --check`：通过。

### 真实浏览器 / API

- 本地 Vite 前端连接真实 Compose API；使用真实 `local-admin`、真实空间和真实服务返回，不使用截图专用 Mock。
- M9-FE 收尾复核后已重建 Compose `web` 镜像并仅替换 Web 容器；`http://127.0.0.1:8080/` 健康。2026-09-02 补充前端优化后再次重建并替换 `web` 容器，产物指纹为 `index-CMB7_oGh.js` / `index-CIigTlfO.css`，真实登录后确认移动页面选择器、快速导航按钮、长密级指标和产品级浏览器标题已生效。
- Compose API、PostgreSQL、Redis、RustFS、Temporal、ClamAV、parser sandbox、Web 均处 running/healthy（Worker 无单独 healthcheck，处 running）。
- graph query 切换及浏览器 back/forward：`页面知识图谱 → 关系图谱 → 页面知识图谱 → 关系图谱`，URL/query 与页面一致。
- Wiki 页面选择：`?page=<id>` 在 reload 后仍恢复同页。
- Task：`/tasks → /tasks/:id → back /tasks → forward /tasks/:id`，详情清除/恢复一致。
- 干净会话打开 graph：控制台 error/warn 为 0。
- 键盘 Tab：焦点落于导航按钮并显示 2px solid outline；`Ctrl/Cmd+K` 有组件回归覆盖。

### 视觉

- 视口：1440×900、1024×768、390×844。
- 51 个受保护路由/视口组合逐一验证 pathname、H1、scroll position 和 document width；0 个 body 横向溢出。
- 2026-09-02 补充巡检复跑 54 个路由/视口组合：0 横向溢出、0 可见元素越界、0 小尺寸可见控件、0 控制台 warn/error；移动导航选择器与快速导航真实交互通过。
- 登录三视口 document width 均与 viewport 相等。
- 截图路径：`docs/development/evidence/m9-fe/{baseline,final}/`。
- 补充截图路径：`docs/development/evidence/m9-fe/followup-2026-09-02/`。

### 未执行项

- 未运行国产浏览器/多浏览器矩阵、远程 CI 或自动像素差异；当前任务使用本地 Chromium 真实交互、全路由截图和人工独立审查。
- 未运行 Python/API/契约测试；本次没有修改后端、公共 API、OpenAPI、SDK、领域、Workflow 或迁移。真实 API 冒烟已由浏览器与 Compose 状态覆盖。

## 7. 迁移影响

- 数据库迁移：无；未创建、修改或执行迁移。
- API/契约影响：无；请求、ETag、幂等、tenant/space、clearance、错误和状态机语义不变。
- 路由兼容性：新增真实 `/tasks` 导航；`/tasks/:id` 为新主路径，继续兼容 `/compile/:id`；其他路由不变。
- 依赖影响：无。`package.json` 与 lockfile 无 M9-FE 变更；无新增许可证或供应链面。

## 8. 安全、权限、审计与证据检查

- 前端未绕过服务端 RBAC/ABAC、密级或审核职责分离；Admin 不可见/不可用与 403 页面仍保留，服务端继续复核。
- 真实 safe-error、空、加载、冲突和权限结果未被改为成功；原型 Mock 没有进入运行时。
- 无远程字体、图片、CDN、凭据、Cookie、API Key、内部地址或敏感日志新增。
- 未修改 Evidence、SourceAnchor、Claim、Release、审计或 Workflow 语义；截图只包含已有本地开发/合成测试数据。

## 9. 需求追踪

- 新增：NXW-FE-001—NXW-FE-005。
- 治理决策：OQ-GOV-016。
- 未完成 M9-FE 项：无。
- 不由 M9-FE 关闭：M9 专家身份、批准阈值、真实评审记录和公开资料逐份准入仍为 P0。

## 10. 独立审查、风险与遗留

- 首轮审查 P0：0。
- 审查阶段 P1：8 类，均已修复并新增代码/浏览器/截图证据。
- 最终复核：P0/P1 清零；建议本地技术验收。
- P1：无。
- P2：国产浏览器/多浏览器矩阵、远程 CI 和自动像素差异未执行；`SourceCenter.tsx`、`TaskCenter.tsx` 仍有少量真实的 M2/M3 能力边界文案，可在后续产品文案治理中语义化；以上均不阻断本地技术验收。
- M9 业务 P0：仍开放，未被本报告静默关闭。

## 11. 停止声明

已完成 M9-FE 实施、独立审查修复和本地技术验收，并停止在 M9-FE。未自行进入 M10；未实施 M10 权限、多空间运营或其他未授权能力。
