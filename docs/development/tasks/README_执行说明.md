# NEXWEAVE 完整分阶段开发任务书 V1.0

本包包含：

- 完整开发任务总纲；
- 已有M-1编码前准备任务书；
- M0—M15独立Codex开发任务书；
- M0-Lite（LL0）本地轻量纵向闭环补充任务书；
- NEXWEAVE PRD、原型与交付说明副本。

## 推荐执行顺序

1. 先执行M-1并验收；
2. 每次只下发一个Milestone；
3. Codex完成后停止并提交回报；
4. 由产品/架构负责人验收后再下发下一阶段；
5. R1在M9完成，R2在M12完成，R3在M15完成。

## Local Lite 补充执行轨道

在开发设备暂不具备 Docker Compose、PostgreSQL、RustFS、Redis 和 Temporal 完整运行条件时，可在 M-1 基线后执行 `M0-Lite（LL0）`：

1. Local Lite 以本机真实业务闭环为目标，允许使用 SQLite、本地文件对象存储、本地 Workflow Runner 等可替换 Provider；
2. Local Lite 不替代正式 M0—M15，也不降低真实基础设施、E2E、性能、高可用和灾备门禁；
3. Local Lite 按 LL-0—LL-5 子阶段逐一执行和验收；
4. Local Lite 验收后先进入 Local Real，再进入正式 Docker Compose 和后续规模部署路线。

具体范围、架构边界和验收标准见 `18_NEXWEAVE_M0-Lite_本地轻量纵向闭环任务书_V1.0.md`。

## 注意

任务书默认使用Markdown，适合直接放入项目根目录或 `docs/development/tasks/`。
