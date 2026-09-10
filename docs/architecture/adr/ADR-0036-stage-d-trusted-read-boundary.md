# ADR-0036：阶段 D 固定发布读取与验收收口

Status: Accepted for implementation under explicit Stage D scope selection.
Date: 2026-09-09.

1. Query 新建与历史读取均按当前权限、源密级、未失效/未归档源、ACCEPTED Evidence、VALID Anchor、同 Release Claim/Evidence 成员筛选。回答/依据/命中正文使用冻结 Claim，不使用未获引用的召回文本。当前保留的引用与陈述一一对应；历史记录不写回。
2. 历史答案增加可选 `read_checked_at` 与 `read_filtered` 响应元信息，表示当前授权下的读取投影；不修改数据库。重放同时匹配 Release、问题、检索策略/参数，冲突返回 409，不返回别的请求答案。当前未发布 Conflict 明细不混入固定发布答案，uncertainty 明示需另行查看有权限的冲突工作台。
3. Graph 节点/关系内容来自 ReleaseItem.snapshot。起点和可选终点必须属于该 Release 且当前可见，不满足时统一 404；冻结实体版本的编译源仍受当前密级和失效/归档约束。关系及所引用 Evidence 必须是同一发布成员，当前证据/Anchor 和来源有效才可遍历。
4. 不再从当前 knowledge_entities/relations 文本补图。单次读取最多 2000 个关系、4000 个实体；超过预算明确失败，不返回假完整图。遍历输出最多 500 边，触达输出预算标记 truncated；最短路径搜索在受限完整候选图中进行。参数与时间值显式类型转换，避免 NULL SQL 参数歧义。
5. 业务含义仍按 ADR-0026：正式发布唯一权威、读时证据门禁、抽取式问答。修复不改变旧 Release/Evidence/答案/Forecast 的存储内容，不修改历史迁移或引入供应商/领域分支。C 组合读取复用加强后的 Query，保留其最终门禁。
6. 以真实浏览器与隔离合成数据验证，不冒充现场专家/工业验收；不宣称未覆盖的所有接口已经全面安全认证。模型与依赖版本保持，停止在 D/M9.5。

读取补充：历史答案的原问题文本同样可能包含敏感输入，读取者密级不得低于 QuerySession.policy_snapshot 记录的创建时密级；不足时整体拒绝，而非仅隐藏 Citation。Graph as_of 使用带时区的日期契约，错误日期由请求校验返回 422。

实现核验补充（2026-09-10）：多来源 Claim 的当前密级取全部冻结 Evidence 来源的最高等级，包括已经失效的来源，防止借仍有效的低密级引用暴露整条主张。实体快照只投影现有契约中的标识、类型、规范键和名称；不假设存在 attributes。前端展示图谱截断并清除跨版本旧响应；原文入口统一为站内路径。
