# NEXWEAVE 前端设计系统基线（M9-FE）

> 2026-09-07 更新：本文保留为初轮高保真原型对齐基线。当前系统级整改规范以 `FRONTEND_DESIGN_SYSTEM.md` 为准；桌面 Web 是本轮验收范围，移动端未做专项质量声明。

> 状态：Frozen for implementation  
> 日期：2026-09-01  
> 权威输入：M9/M9-FE 任务书、ADR-0029/0030、高保真交互原型 V1.0、已验收 M1—M8 Web/API 契约  
> 适用范围：`apps/web`；不修改 API、领域状态、Evidence、Release 或权限语义

## 1. 页面、原型、API 与状态映射

| 真实路由 | 原型页 | 界面模式 | 真实 API / 数据边界 | 必须保留的状态 |
|---|---|---|---|---|
| `/overview` | 总览 | Dashboard | spaces、audit read projections | loading、权限不足、空、错误、真实计数 |
| `/spaces` | 知识空间 | Admin / List-Detail | organizations、spaces、members、users | ACTIVE/ARCHIVED、ETag、权限、空、错误 |
| `/sources`、`/source-versions/*` | 资料中心 | List / Detail / Upload | sources、uploads、versions、parse jobs、segments、anchors | upload/scan/parse/partial/OCR/stale/error/retry |
| `/tasks`、`/tasks/:id`（兼容 `/compile/:id`） | 编译中心的运行任务区域 | Operational List-Detail | workflow tasks、commands、reconcile | queued/running/waiting/paused/failed/cancelled/completed |
| `/compile` | 编译中心 | Workbench / Form | compile jobs、schemas、sources、prompt/model profiles | fixed inputs、running、failed、retry、empty、error |
| `/schemas` | Schema Studio | Canvas / Inspector | schemas、composition validation、publish | DRAFT/PUBLISHED、conflict、validation error、permission |
| `/domain-packs` | 领域知识包 | List / Detail / Form | domain packs、installations、schema composition | install/disable/rollback、signature/checksum、error |
| `/wiki` | Wiki | Workbench | wiki pages、versions、diff/edit | generated/protected、stale ETag、empty、error |
| `/graph`、`/graph?view=release` | 关系图谱 | Canvas / Graph | wiki link graph 或固定 Release graph | selected/focus/filtered/empty/permission/error |
| `/claims` | 主张与证据 | Review / Evidence | accepted claims/evidence | support/counter、anchor validity、empty/error |
| `/conflicts` | 冲突中心 | Review / Diff | conflicts、resolution action | open/resolved/blocked、ETag、permission/error |
| `/reviews` | 审核中心 | Review / Workflow | review cases/tasks/actions | stage、separation of duties、return/reject/approve/error |
| `/quality` | 质量中心 | Dashboard / Form | evaluation suites、schemas、claims | gate/result/error/empty/running |
| `/releases` | 发布中心 | List / Detail / Approval | candidates、releases、evaluation inputs | immutable/publish/blocked/deprecated/error |
| `/ask` | Ask NEXWEAVE | Workbench | fixed Release query | cited answer/refusal/error/loading/idempotent replay |
| `/integrations` | 集成中心 | Admin / List-Form | connector instances、sync runs | read-only allowlist、sync status、error、empty |
| `/admin` | 系统管理 | Admin / Tabs | users、roles、audit、model/prompt/connector governance | role visibility、permission denied、empty/error |
| `/login`（未认证态） | 登录入口 | Authentication | local development identity 或 OIDC boundary | working/error/disabled；不得伪装生产认证 |

原型中的固定 KPI、演示资料、假任务编号、假连接状态、假 Release、模拟问答、SAP/达梦/远程模型状态及点击后本地伪成功均不进入真实产品。全局搜索在本阶段只检索真实可达导航，不伪装知识检索 API。

## 2. 界面模式

- Dashboard：总览、质量；密集指标 + 风险/活动分区，避免巨型 Hero。
- List / Detail：空间、资料、任务、Pack、发布、集成；左侧选择与右侧详情在窄屏顺序堆叠。
- Workbench：编译、Wiki、Ask；主工作表面 + 检查器/Evidence 区，桌面多栏、窄屏单栏。
- Canvas / Graph：Schema、Wiki 图、Release 图；独立画布表面、工具栏、图例和属性面板。
- Review / Diff：Claim/Evidence、冲突、审核；保留风险强度、证据与确认语义。
- Admin / Form：空间与平台管理；紧凑表单、明确权限和不可用状态。

## 3. 设计 token

唯一代码权威为 `apps/web/src/styles/tokens.css`。语义冻结如下：

- 背景：`canvas #090a0f`、`sidebar #0d0f16`、`surface-1 #11131b`、`surface-2 #151824`、`surface-3 #1b1f2d`。
- 边界：默认 `#292e40`，强调边界使用低透明紫/青；不以多层阴影代替结构。
- 文字：主 `#f4f5fb`、次 `#aab0c3`、弱 `#747c92`、反色 `#090a0f`。
- 品牌：violet `#8467ff`、cyan `#31d9ff`、lime `#d9ff55`；语义 success `#44e39c`、warning `#ffbd59`、danger `#ff6c88`、info `#68a7ff`。
- 字体：本地系统字体栈；中文优先 PingFang SC / Microsoft YaHei；ID、checksum、数据使用系统等宽栈；不加载远程字体。
- 尺寸：4px 基准网格；间距 4/8/12/16/20/24/32/40；控件高度 32/36/40；正文 12—14px；页面标题 24—32px。
- 形态：圆角 6/10/14/18px；边界 1px；主面板只使用一层受控阴影；图标 16/20/24px。
- 布局：侧栏 248px、顶栏 64px、内容最大宽度 1500px；工作台使用 `minmax(0, 1fr)` 防溢出；1024px 以下收紧，760px 以下侧栏转为横向可滚动导航和单栏内容。
- 动效：fast 120ms、normal 180ms、slow 260ms，标准 ease；`prefers-reduced-motion` 下取消非必要动画和滚动行为。
- 层级：sticky 20、dropdown 40、drawer 60、modal 80、toast 100；不得在 feature 中自建更高层级。

## 4. 组件契约

代码权威为 `apps/web/src/design-system/`。

- Shell：`AppShell`、Sidebar、SpaceSwitcher、Topbar、QuickNavigation、ContentRegion。负责布局、可恢复路由入口、空间切换、身份状态与退出；不负责业务数据变造。
- 基础输入：Button/IconButton/Input/Select/Textarea/Checkbox/Switch/Tabs/SegmentedControl 使用原生语义；disabled 与 loading 可区分；焦点必须可见。
- 数据展示：Panel/Card/Metric/Badge/StatusPill/DataTable/ListRow/Toolbar；长 ID 可换行或省略并保留 title；表格在窄屏水平滚动。
- 浮层：Modal/Drawer/Popover/Tooltip/Toast 预留统一层级与焦点契约；当前业务没有真实浮层时不得仅为视觉创建假交互。
- 状态：LoadingState/Skeleton/EmptyState/ErrorState/PermissionDenied/StaleState；错误不得被空态吞掉，重试必须调用原操作。
- 工作台：SplitPane/WorkbenchLayout/InspectorPanel/EvidencePanel/GraphSurface/DocumentSurface；桌面分栏，窄屏按主内容→证据/属性顺序重排。
- 可访问性：可交互元素使用 button/link/input 等原生控件；`focus-visible` 清晰；图标按钮具备 label；状态不仅依赖颜色；破坏性操作保留确认与服务端权限结果。

## 5. 图标与依赖策略

- 不新增运行时或开发依赖。使用受控内联 SVG/CSS 图形与系统字体，避免远程图片、字体和 CDN。
- 优点：离线可用、无新增许可证/供应链面；风险：图标集合需人工维护一致性。
- 替代方案：未来若图标规模显著增长，可经依赖治理引入锁版、tree-shakable 的 MIT 图标包；删除方案为回退当前内联图标映射。
- 截图使用现有浏览器控制能力，不将 Playwright 等新包写入产品依赖。

## 6. 迁移批次与停止点

1. Shell + tokens + foundation：登录、空间恢复、权限导航和退出回归后停止检查。
2. 样板页：总览、资料中心、Wiki、Schema/图谱；三视口与异常状态回归后冻结样板。
3. 业务页：空间、任务、编译、Pack、Claim/Conflict/Review、Quality/Release/Ask、Integration/Admin。
4. 特殊画布：Wiki Link Graph、Release Graph、Schema；键盘/触控/裁切检查。
5. 清理：移除旧绿色主题权威、重复基础组件和死样式；完成全门禁与全路由截图。
6. 独立审查：P0/P1 清零后复验并输出报告；停止在 M9-FE。

`App.tsx` 只保留会话、数据与路由编排；Shell 和共享展示组件移入设计系统。`SourceCenter.tsx` 本阶段优先消除重复基础组件并保留其成熟的数据/操作边界，不重写 M3 业务状态机。

## 7. 有意偏离原型

- 原型的品牌视觉与信息层级保留；静态 KPI、假资料、假连接、假 Release 和模拟按钮行为全部舍弃。
- 原型固定 250px 侧栏在移动端不可用，真实实现改为顶部品牌/空间区 + 横向可滚动导航。
- 原型部分文字和控件小于可访问基线，真实实现保持至少 12px 信息文字、36px 常用触控高度和清晰焦点。
- 原型的 Global Search 改为真实导航快速切换；知识检索继续由 Ask/已验收 API 承担。
- 原型页面为隐藏/显示单页状态，真实实现继续使用 URL、History 和刷新恢复。

## 8. 验证基线

- 编码前：format、lint、strict typecheck、18 项 Vitest、production build 均通过。
- 基线截图：`docs/development/evidence/m9-fe/baseline/`，视口为 1440×900、1024×768、390×844。
- 最终验收：相同视口、稳定真实 API 状态、全部主路由；同时检查长文本、空/错误/权限、焦点、减少动画与控制台错误。
