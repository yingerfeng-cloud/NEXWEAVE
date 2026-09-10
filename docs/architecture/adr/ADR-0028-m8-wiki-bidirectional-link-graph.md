# ADR-0028: M8 Wiki 双向链接知识图谱投影

- Status: Accepted
- Date: 2026-08-31
- Approval basis: 用户要求 NEXWEAVE 必须提供 Obsidian 风格双向链接知识图谱展示
- Decision owners: 产品、架构、安全负责人
- Related: NXW-WIKI-001, NXW-WIKI-002, NXW-NFR-SEC-003

## Context

M5 已保存 `wiki_page_links`，并能在单页读取出链与反向引用，但缺少可浏览整个知识空间、定位相邻页面的图谱视图。用户要求原生提供 Obsidian 风格的知识图谱展示；该能力不能把本机 Obsidian 或导出的 Markdown 目录变成平台权威来源。

## Decision

1. 新增只读 `Wiki Link Graph` API，按空间和 `page.read` 权限返回页面节点及现有链接边。节点来自当前 NEXWEAVE Wiki 页面；边来自现有 `wiki_page_links`，不推断、不补写、不产生事实、证据或 Release 内容。
2. 页面链接保持有向事实：源页的 Wiki 链接是出链，目标页的 backlink 由同一链接反向可达。图谱 UI 同时展示两方向邻接关系，以实现 Obsidian 风格的双向浏览；这不等同于为每条边写入镜像边。
3. 图谱是 Wiki/Draft 的导航投影，和 M7 的 Release Relation Graph 严格分离。它可展示草稿页面，不表示已发布知识、已审核 Claim 或 Evidence 支持；界面必须清楚标注该范围。
4. 服务端强制节点、边与遍历深度上限；无焦点时返回稳定排序的有界空间投影，有焦点时按出链和反向引用作有界 BFS。超出上限时返回 `truncated`，前端不得伪装为全量。
5. 前端采用本地 SVG 布局渲染，无额外图数据库、图计算服务或远程浏览器依赖；提供标题搜索、按页面模板着色、图例、焦点邻域、缩放和点击打开 Wiki 页面。

## Compatibility and migration

- 复用 M5 `wiki_pages` 与 `wiki_page_links`，不新增迁移，也不修改历史链接或页面版本。
- 新增版本化公共契约和只读 API；Python/TypeScript SDK 可安全渐进采用。
- 不改变 ADR-0024 的追加式 Wiki、ADR-0026 的 Release Graph，或 ADR-0027 的 Obsidian 交换/回导边界。

## Validation

- 契约/API：租户和空间隔离、`page.read` 授权、焦点不存在、深度/容量上限、出链与 backlinks 共同可达、`truncated` 语义。
- UI：搜索、模板颜色图例、节点选择/邻域、链接方向提示和打开页面动作均有自动化测试；构建、静态检查与既有测试全量通过。
