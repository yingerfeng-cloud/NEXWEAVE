# NEXWEAVE 前端设计系统

> 版本：M9-FE System Refactor / 2026-09-07  
> 代码权威：`apps/web/src/styles/tokens.css` 与 `apps/web/src/design-system/`  
> 适用：桌面 Web；不改变 Domain Model、API Contract、权限、Evidence 或 Release 语义

## 1. 产品语言

设计关键词为 Trusted、Structured、Traceable、Governed、Versioned、Evidence-grounded。暗色主题表达克制、严谨的企业知识工作台，不使用 Hacker Console、赛博霓虹或 Crypto Dashboard 语言。

界面以可信知识生命周期串联，而不是把 17 个 Route 当作孤立 CRUD：

`资料 → 解析 → 建模 → 主张与证据 → 冲突 → 审核 → 质量 → 发布 → Wiki / 图谱 / Ask`

## 2. 信息架构与 Shell

- 工作台：总览、知识空间、资料、任务、编译。
- 知识建模：Wiki、Schema Studio、领域包、知识图谱。
- 知识治理：主张与证据、冲突、审核、质量、发布。
- 智能使用：Ask NEXWEAVE。
- 系统：集成、平台管理。

Sidebar 宽 16.5rem，Topbar 高 4rem，内容最大宽 110rem。空间选择只在 Sidebar，Topbar 显示当前任务上下文。分组允许折叠，路由不使用里程碑编号。

## 3. 核心 token

- 背景：canvas `#0b0d12`，sidebar `#0f1218`。
- Surface：`#12161e` / `#171c25` / `#1c222d`，raised `#222a36`。
- 边界：默认 `#2b3442`，强调 `#465264`。
- 文字：primary `#f2f5f8`，secondary `#c3cad4`，muted `#98a3b2`。
- 品牌/交互：primary `#8092e8`；仅用于主动作、Active 与 Focus。
- 语义：success `#62c79b`，warning `#d8a657`，danger `#df7888`，info `#7ba4dc`。
- 4px 间距网格；圆角 6/10/14/18px；动效 120/180/260ms。
- 正文与表单 14px；次级信息 12—13px；元数据 11—12px；页面标题 28—32px；主要业务信息不得降到 10px。

颜色不是唯一状态信号；状态同时包含中文标签或说明。KPI 不使用无语义彩边，Surface 主要依赖间距、Divider 和有限边框建立层级。

## 4. 组件契约

- `AppShell`：Sidebar、Workspace Switcher、Topbar、Command Search、User/Role、Developer Mode。
- `PageHeader` / `Panel` / `Metric` / `DataTable`：统一页面层级和信息密度。
- `EmptyState`：必须包含 icon、title、description，可提供 primary/secondary action。
- `ErrorState`：局部错误就地显示，可重试；不以整页红色 Banner 覆盖其他可用内容。
- `StatusPill`：稳定状态值映射为中文业务标签，保留原值在 title 供诊断。
- `GovernanceStepper`：主张与证据、冲突、审核、质量、发布共用五阶段表达。
- `TechnicalDetails`：内部 ID、checksum、workflow/run、JSON 和原始诊断信息的唯一降级容器。
- `AppErrorBoundary`：捕获页面渲染故障，生产界面提供安全恢复，不显示 stack。

## 5. 错误与开发信息

`ApiError` 统一分类：ACCESS_DENIED、NOT_FOUND、PRECONDITION_FAILED、VALIDATION_ERROR、CONFLICT、NETWORK_ERROR、SERVER_ERROR、UNKNOWN。生产 UI 只显示安全中文文案；code、request id、raw message、stack 仅允许在技术详情或 localhost Console。

Developer Mode：

- 只在 localhost/127.0.0.1/::1 出现；
- 默认关闭；
- 关闭时过滤 M*、E2E、synthetic、stub、isolated、failure audit、technical pilot 等测试空间/用户；
- 不改变服务端权限或业务状态。

## 6. 页面模式

- Dashboard：总览、质量。
- Master–Detail：知识空间、任务、主张。
- Data Table：资料、领域包、Admin。
- Workflow：编译、冲突、审核、发布、集成。
- Studio：Schema Studio、Wiki Workbench。
- Explorer：知识图谱。
- Chat：Ask NEXWEAVE。
- Settings：平台管理。

JSON 只进入 Advanced/Source View；内部 ID、Source Anchor、运行 ID 和校验和只进入 Technical Details。Label 位于控件上方，Primary、Secondary、Ghost、Danger、Disabled 必须可区分。

## 7. 桌面布局与可访问性

- 支持 1366×768、1440×900、1920×1080、2560×1440 的 fluid grid 与 `minmax(0, 1fr)` 防溢出。
- Dashboard/Studio 合理使用宽屏；阅读内容保持适当行长，不把所有页面锁定为同一窄宽度。
- 原生 button/input/select/textarea 保留键盘语义；`focus-visible` 明确；Disabled 同时使用形态、透明度和原生属性。
- `prefers-reduced-motion` 下取消非必要动画。
- 本轮按用户指令不做移动端专项适配或验收；现有兼容样式保留，不视为本轮质量声明。

## 8. 依赖与治理

- 本轮不新增依赖，不加载远程字体、图片或 CDN。
- 组件不绕过服务端 RBAC/ABAC、密级、审核职责分离、Evidence 和不可变 Release。
- 新 UI 不伪造数据、连接成功、发布状态或问答结果。

