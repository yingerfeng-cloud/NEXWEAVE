# NEXWEAVE 前端 UI 审查

> 审查日期：2026-09-07  
> 范围：`apps/web` 与本地 Compose `web` 运行态  
> 依据：《NEXWEAVE Frontend UX/UI System Refactor》、M9-FE 边界与当前 M1—M9 契约  
> 结论：P0 已关闭；部分 P1/P2 深化项保留为 PARTIAL；本轮不宣称“全部完成”

## 1. 范围与回滚判断

- 本轮只处理前端信息架构、设计系统、页面布局、错误呈现、状态表达和生产/测试数据隔离。
- 按用户指令，桌面 Web 为验收主场景，验证 1366×768、1440×900、1920×1080、2560×1440；未投入移动端专项整改或回归。
- 不整体回滚上一轮。上一轮的 token、App Shell、真实路由和 API 接入是可复用基线，整体回滚会丢失有效工作，并可能覆盖同一脏工作区中的 M3—M9 既有改动。
- 采用选择性修正：保留正确基础，替换研发态文案、结构与展示层；未执行 `reset`、`revert` 或历史迁移回退。

## 2. 审查方法

- 源码审查：导航、错误入口、表单、状态、空态、技术详情、生产夹具过滤及禁止词扫描。
- 自动门禁：format、strict typecheck、lint、22 项 Vitest、production build、diff whitespace。
- 运行态审查：真实本地 API 与 Compose `web`，不注入截图 Mock。
- 视觉抽查：四种指定桌面视口各选一个代表性任务页，检查页面级横向溢出、研发词泄露、信息层级和可读性。
- 交互抽查：一级路由切换后滚动位置由 242px 复位到 0；浏览器 error 日志为 0。

## 3. 发现与处置

| 级别 | 原问题 | 处置 | 状态 |
|---|---|---|---|
| P0 | 后端 detail/message 可直接进入页面 | 引入 `ApiError` 分类、统一中文安全文案、Widget 级 ErrorState 与 `AppErrorBoundary`；原始细节仅本地控制台 | PASS |
| P0 | Production UI 暴露 M*/E2E/技术试点空间和测试用户 | 默认过滤开发夹具；Developer Mode 仅 localhost 可见且默认关闭 | PASS |
| P0 | 导航以 01—17/Milestone 排序，Ask 位于系统 | 改为五个业务分组、移除编号、Ask 迁入“智能使用”、分组可折叠 | PASS |
| P0 | 字号偏小、荧光/渐变/Glow 过强、KPI 彩色底边 | 正文 14px，建立克制的企业暗色语义色，减少 Glow/渐变，移除装饰性 KPI 彩边 | PASS |
| P0 | 空态只说明“无数据”，表单与按钮状态不统一 | 统一 `EmptyState`、标签、辅助文案、主次动作、Disabled 与状态 Pill | PASS |
| P0 | 页面切换保留旧滚动位置 | location 变化时复位到页面顶部 | PASS |
| P1 | 总览是低价值指标和大块审计 | 改为知识资产、待审核、冲突、当前发布、质量状态及生命周期；审计降级到次级区域 | PASS |
| P1 | 编译是技术字段横排 | 改为选择知识版本、选择配置、前置检查、提交与结果区的 Guided Workflow | PASS |
| P1 | Wiki/Ask/Schema/治理页面结构相同 | 分别形成三栏 Workbench、Chat + Evidence Inspector、Studio、五阶段 Governance | PASS |
| P1 | 知识空间详情过薄 | 已形成 Master–Detail；尚未补齐建议的七个完整业务页签 | PARTIAL |
| P1 | 资料导入常驻且技术字段突出 | 改为按需展开导入与高级设置；尚未形成完整五阶段 Drawer/Modal 导入向导 | PARTIAL |
| P1 | Schema 主要是 JSON 表单 | JSON 已降级为高级源码视图；Object/Property/Relation 的完整可视化编辑器未实现 | PARTIAL |
| P2 | 图谱缺完整 Explorer 控件 | 已有搜索/筛选/缩放/重置和任务型画布；Fit View、布局算法选择与完整右侧属性面板待深化 | PARTIAL |
| P2 | Admin 缺少产品化筛选/创建 | 已有搜索、状态筛选、创建弹窗和语义 Badge；角色筛选与显式分页待补 | PARTIAL |

## 4. Route 前后结构

| Route | 整改前 | 整改后 | 结论 |
|---|---|---|---|
| `/overview` | 工程指标 + 大审计区 | Dashboard + 可信知识生命周期 | PASS |
| `/spaces` | 列表与薄详情 | Master–Detail | PARTIAL |
| `/sources` | 常驻导入 + 技术状态 | 资料表格 + 按需导入 + 业务状态 | PARTIAL |
| `/tasks` | 工作流/基础设施视角 | 任务 KPI + Master–Detail + 执行时间线 | PASS |
| `/compile` | 技术字段长表单 | Guided Compile Workflow | PASS |
| `/wiki` | 通用卡片页面 | 页面目录 / 正文 / Evidence 三栏 Workbench | PASS |
| `/schemas` | JSON 表单 | Schema List + Editor + Advanced Source View | PARTIAL |
| `/domain-packs` | 技术安装表单 | 可信制品目录 + 安装状态 | PASS |
| `/graph` | 通用图谱卡片 | Explorer 画布 | PARTIAL |
| `/claims` | 独立列表 | Claim List + Evidence Detail + Governance Stepper | PASS |
| `/conflicts` | 独立空卡 | 冲突处置工作流 + Governance Stepper | PASS |
| `/reviews` | 独立空卡 | 审核工作流 + Governance Stepper | PASS |
| `/quality` | 独立表单 | 质量门禁 + Governance Stepper | PASS |
| `/releases` | 候选/发布列表 | 发布流程 + Governance Stepper | PARTIAL |
| `/ask` | Select + Textarea + Button | Chat Workspace + Release Context + Evidence Inspector | PASS |
| `/integrations` | Definition ID + JSON | Connector Catalog + 实例创建流程 + Advanced JSON | PARTIAL |
| `/admin` | 裸输入与技术 ID | Settings/Data Table + Filter + Create Modal | PARTIAL |

## 5. 剩余风险

- 尚未进行正式 WCAG 对比度仪器审计、多浏览器矩阵或自动像素差异；当前证据是本地 Chromium、键盘/焦点代码审查与人工视觉检查。
- 少数深层执行日志仍展示服务端业务事件文本；它们属于任务审计内容，不经过通用错误适配器。若事件源可包含非产品化英文，后续需在契约层增加稳定展示文案字段。
- 没有新增“最近问题”、完整图谱布局选择、Schema 可视化建模、Admin 显式分页等能力，因为现有 API/数据契约不足或任务优先级较低；本轮不使用 Mock 冒充完成。
- M9 专家身份、批准阈值、真实 Review/Evaluation/Release/Query 证据仍为业务 P0，本前端整改不关闭这些事项。

