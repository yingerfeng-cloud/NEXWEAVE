# NEXWEAVE M9.5 前端交互深化记录

> 日期：2026-09-10  
> 范围：M9.5 时态知识 / Chronos-2 前端交互延续整治  
> 判定：本地技术验证通过，待用户确认  
> 停止边界：停留在当前前端范围，不进入 M10

## 1. 完成范围

- 时态知识工作台明确展示 Chronos-2 提供方、预测运行状态、队列/运行/待投递数量、Worker 数量和实现版本。
- 预测场景表单增加未来路径、历史窗口、预测步数和阈值的即时校验；运行中任务防重复提交；可恢复最近输入；提交按钮明确冻结输入语义。
- 运行记录补齐状态、提供方、创建时间、错误码、取消/冻结输入重试和刷新入口；离线时保留记录并提供可恢复提示。
- 预测图增加历史窗口切换、P10–P90 区间、P50/峰值摘要、输入截止点与预测末端提示；同窗口场景比较保持只读并拒绝不兼容制品。
- 已发布知识回接要求显式选择 Release 与问题，查询期间防重复提交；切换版本或问题会清除旧结果；无引用、版本弃用和原文定位均有清晰反馈。
- 新增绑定改为真正的遮罩弹层，首焦点落在关闭按钮，支持 Escape 关闭、遮罩点击关闭、资源失败重试和明确的按钮类型/无障碍名称。

## 2. 变更文件

- `apps/web/src/LivingKnowledge.tsx`
- `apps/web/src/living.css`
- `apps/web/src/BindingWizard.tsx`
- `apps/web/src/ForecastKnowledge.tsx`
- `apps/web/src/ForecastComparison.tsx`
- `apps/web/src/livingTypes.ts`

未修改 API、领域模型、Workflow、OpenAPI、数据库迁移或依赖。

## 3. 独立审查与验证

- 代码审查：复核异步响应失效、运行轮询依赖、幂等键复用、表单边界校验、旧结果清除和弹层关闭路径；修复 Hooks 依赖提示及无障碍查询名称问题。
- 定向前端测试：4 个文件、7 项通过（ForecastKnowledge、LivingKnowledge、BindingWizard、livingComparison）。测试中的离线/网络异常为受控回归场景，不代表生产故障。
- `npm run lint`：通过，0 warning。
- 目标文件 Prettier 检查：通过。
- `npm run build`：通过，54 modules；产物 `index-CfNFE1lY.js` / `index-DviyMVkb.css`。
- Compose Web：已重建并替换 `web` 容器，容器健康；浏览器使用新资源指纹打开 `/wiki?view=living`，确认状态栏、Chronos-2 标签、弹层和历史窗口切换生效。

## 4. 可信边界与风险

- 本轮仅优化已有真实 API 的呈现与交互，没有新增静态 Mock、固定 JSON 或伪造成功状态。
- 页面继续显式标注合成/未经核实数据；预测、Potential Event 和知识回接不被呈现为工业验收、故障诊断或已发布 Evidence。
- 未运行与本次无关的 Python/API 全量测试、多浏览器矩阵或远程 CI，以控制额度；后端与数据库未变更，定向前端验证足以覆盖本轮风险。

## 5. 需求追踪与停止声明

- 覆盖 M9.5 纵向首片中“历史窗口、显式未来输入、Chronos-2 运行状态、运行记录、条件比较和已发布知识回接”的前端交互要求。
- 不关闭 M9 专家身份、批准阈值、真实评审记录或工业效果验收等既有 P0。
- 已完成本轮前端实施、独立审查和本地技术验收；现在停止，不进入 M10。
