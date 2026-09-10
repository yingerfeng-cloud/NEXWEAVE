# NEXWEAVE Frontend UX/UI System Refactor 报告

> 执行日期：2026-09-07  
> 范围：M9/R1 前端补充整改  
> 判定：本地实施、独立复核批次与技术验收完成；存在明确 PARTIAL 项；待用户验收  
> 停止边界：M9-FE，不进入 M10

## 1. 结果摘要

本轮没有整体回滚上一轮，也没有重写后端。保留已验证的设计系统和真实 API 接入，在其上完成全局错误适配、生产/测试数据隔离、导航重组、中文业务状态、页面任务化布局、桌面大屏优化与容器更新。

当前 `http://127.0.0.1:8080/` 已由新 web 镜像提供。初次仅启动 web 时因 `api` DNS 不存在进入重启循环；启动 Compose `api` 及声明依赖后，API 健康并带起 web。该问题属于运行依赖未启动，不是浏览器仍缓存旧界面。

## 2. 实际完成范围

- `ApiError`、`messageOf`、`AppErrorBoundary` 与局部 ErrorState 统一错误系统。
- Production UI 默认过滤测试空间/用户；Developer Mode 仅本地可见且默认关闭。
- 五组业务导航、无编号 Sidebar、Ask 移出系统、可折叠分组、路由滚动复位。
- 统一 Typography、颜色、Surface、Button、Form、Status、Empty/Loading/Permission 系统。
- 总览、资料、任务、编译、Wiki、Schema、领域包、图谱、治理、Ask、集成、Admin 形成差异化任务布局。
- 更新旧测试断言但保留全部 22 项测试；新增候选模型技术详情以维持可追溯性。
- 重建并替换 Compose web 镜像；使用真实本地 API 完成四档桌面抽查。

## 3. Route 整改前后清单

| Route | 前 | 后 | 状态 |
|---|---|---|---|
| `/overview` | 工程指标/审计主导 | Dashboard + 生命周期 | PASS |
| `/spaces` | 普通列表/薄详情 | Master–Detail | PARTIAL |
| `/sources` | 常驻导入/技术状态 | Data Table + 按需导入 | PARTIAL |
| `/tasks` | 基础设施任务视角 | 任务 KPI + Detail/Timeline | PASS |
| `/compile` | 技术字段横排 | Guided Workflow | PASS |
| `/wiki` | 通用卡片 | 三栏 Studio/Workbench | PASS |
| `/schemas` | JSON 表单 | List + Editor + Advanced Source | PARTIAL |
| `/domain-packs` | 技术安装表单 | Catalog + 安装状态 | PASS |
| `/graph` | 图谱卡片 | Explorer | PARTIAL |
| `/claims` | 列表 | Claim Master–Detail | PASS |
| `/conflicts` | 独立卡片 | Governance Workflow | PASS |
| `/reviews` | 独立卡片 | Governance Workflow | PASS |
| `/quality` | 独立表单 | Governance / Quality Gate | PASS |
| `/releases` | 候选/发布列表 | Governance / Release Flow | PARTIAL |
| `/ask` | Select + Textarea | Chat + Evidence Inspector | PASS |
| `/integrations` | ID + JSON | Catalog + Create Flow | PARTIAL |
| `/admin` | 裸 Input/Table | Settings + Filter + Modal | PARTIAL |

详细审查见 `docs/design/FRONTEND_UI_AUDIT.md`。

## 4. 修改文件清单

### 前端代码

- `apps/web/src/App.tsx`、`api.ts`、`types.ts`。
- `apps/web/src/design-system/AppShell.tsx`、`ui.tsx`。
- `apps/web/src/LoginPage.tsx`、`OverviewPage.tsx`、`SpacesPage.tsx`。
- `apps/web/src/SourceCenter.tsx`、`TaskCenter.tsx`、`CompileCenter.tsx`。
- `apps/web/src/WikiWorkbench.tsx`、`SchemaStudio.tsx`、`PackCenter.tsx`、`WikiLinkGraph.tsx`。
- `apps/web/src/ReviewCenter.tsx`、`M7Knowledge.tsx`、`IntegrationCenter.tsx`、`AdminPage.tsx`。
- `apps/web/src/styles.css` 与 `apps/web/src/styles/*.css`。
- `apps/web/src/App.test.tsx`、`SourceCenter.test.tsx`、`M4Semantic.test.tsx`、`M7Knowledge.test.tsx`。
- `apps/web/index.html`、`Dockerfile`、`nginx.conf` 中既有 M9-FE 前端交付改动继续保留。

### 本轮文档与证据

- `docs/design/FRONTEND_UI_AUDIT.md`。
- `docs/design/FRONTEND_DESIGN_SYSTEM.md`。
- `docs/development/reports/FRONTEND_REFACTOR_REPORT.md`。
- `docs/development/evidence/m9-fe/system-refactor-2026-09-07/*.png`。

仓库同时存在此前 M3—M9 大量未提交改动；本轮未重置、覆盖或将其冒充为本轮新增。

## 5. Acceptance Criteria 对照

| 验收项 | 结果 | 证据 |
|---|---|---|
| 页面不出现 raw backend English error | PASS | 统一 ApiError；错误单测覆盖 401/503；运行态无原始错误主体 |
| Production UI 不显示 M1—M5/E2E/Stub | PASS | 默认夹具过滤；四视口运行态禁止词均为 false |
| Navigation 编号全部移除 | PASS | 17 个入口均无 01—17 |
| Ask 不在“系统”分类 | PASS | 位于“智能使用” |
| 主要正文不低于 14px | PASS | foundation 与页面正文统一 14px；仅次级/元数据使用 12—13/11—12px |
| Empty State 有下一步引导 | PASS | 统一 icon/title/description/actions；DataTable 使用引导空态 |
| 表单 Label 对齐一致 | PASS | 普通字段上置 Label；高级/技术字段折叠 |
| Primary / Disabled 可明确区分 | PASS | 原生 disabled + 透明度/形态/语义样式 |
| 所有一级 Route 进入时滚动正确 | PASS | 运行态 242px → 0；location 变化统一复位 |
| 1920 下无极小字 + 无意义留白 | PASS | Wiki 1920×1080 三栏使用；无横向溢出 |
| Wiki/Schema/Graph/Ask/Governance 为不同任务结构 | PASS | Studio / Explorer / Chat / Workflow 分离 |
| 生命周期可理解 | PASS | 总览生命周期 + 治理五阶段 Stepper + 页面上下游文案 |
| 不修改核心 Domain Model | PASS | 本轮没有 Domain 文件改动或迁移 |
| 不修改既有 API Contract | PASS | 本轮没有 OpenAPI/Contract/API 路由改动 |
| 原有测试不因 UI 重构删除 | PASS | 6 文件、22 项全部保留并通过 |

以上仅是任务书验收项结果，不代表所有建议深化项均完成；Route 级 PARTIAL 见第 3 节。

## 6. 验证结果

- `npm run format:check`：PASS。
- `npm run typecheck`：PASS。
- `npm run lint`：PASS，0 warning。
- `npm test -- --run`：PASS，6 个文件、22 项测试。
- `npm run build`：PASS，46 modules；CSS 52.71 kB（gzip 10.26 kB），JS 312.17 kB（gzip 96.23 kB）。
- `git diff --check`：PASS。
- 浏览器：1366×768 `/overview`、1440×900 `/compile`、1920×1080 `/wiki`、2560×1440 `/ask` 均为 0 页面级横向溢出、0 禁止词；error 日志 0。
- 测试节约：未跑后端全量、远程 CI、移动端、多浏览器或重复 E2E；仅执行与本轮变更直接相关的前端门禁和四个代表性视口。

## 7. Visual Regression 截图

- 基线：`docs/development/evidence/m9-fe/baseline/`。
- [总览 1366×768](../evidence/m9-fe/system-refactor-2026-09-07/overview-1366x768.png)
- [编译 1440×900](../evidence/m9-fe/system-refactor-2026-09-07/compile-1440x900.png)
- [Wiki 1920×1080](../evidence/m9-fe/system-refactor-2026-09-07/wiki-1920x1080.png)
- [Ask 2560×1440](../evidence/m9-fe/system-refactor-2026-09-07/ask-2560x1440.png)

## 8. 尚未整改项与风险

- PARTIAL：知识空间七个完整页签、五阶段资料导入 Drawer/Modal、Schema 可视化模型编辑、图谱 Fit/Layout/完整详情、Ask 最近问题、集成连接测试、Admin 角色筛选/显式分页、发布不可变历史深化。
- 未执行：正式 WCAG 仪器审计、多浏览器/国产浏览器、远程 CI、自动像素差异、移动端专项验收。
- 运行要求：单独启动 web 时，nginx 因找不到 `api` upstream 会重启；应使用 `docker compose up -d api web` 或完整 Compose 启动。
- 本地生产数据为空时，Product UI 会如实展示引导空态；Developer Mode 才能看到合成夹具，不以测试数据伪造完成度。
- M9 专家/阈值/真实评审与 Release/Query 证据仍是 P0，本报告不关闭。

## 9. 迁移、安全与停止声明

- 数据库迁移：无；未新增、修改或执行迁移。
- API/契约：无变更；保留既有权限、ETag、幂等、Evidence、Release 与 Workflow 语义。
- 依赖：无新增；无 lockfile、许可证或供应链扩展。
- 安全：无凭据、Cookie、API Key、远程字体/CDN 或敏感日志新增；服务端 RBAC/ABAC 未绕过。
- 停止：已完成本轮实施、独立复核批次和本地技术验收，停止在 M9-FE；未进入 M10。
