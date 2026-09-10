# ADR-0034：阶段 B 自主绑定与场景比较

Status: Accepted for implementation under user's explicit Stage B instruction (2026-09-09).

1. 保留唯一 SchemaVersion 语义权威与不可变 Binding。领域角色、信号、单位来自已发布 Schema；对象须属于该版本和类型。B 使用已有模型及对象，不另建编辑/审批权威。
2. 增加空间内受控 SourceVersion CSV 预览 GET 和 SignalBinding validate POST；契约限定列/行/样本，输入仅内部 ID，无任意 URL/SQL。先鉴权/密级/源状态/病毒扫描，再由 CsvTimeSeriesConnector 读取并校验固定版本 hash；不返回存储 key。预览/预检写既有审计，validate 无持久业务对象。
3. 抽取原领域 CSV 读取校验，供预检和执行复用。CSV ≤2MB、≤32列、32～20000行；时区、等间隔、有限值和 GOOD 质量规则保持；新增拒绝结构残缺和空/重名列。预检只验证历史数据，不调用模型或制造未来值。
4. 现有创建绑定接口在后端重新执行预检；前端编辑后预检失效，保存仍以服务端为准。复用现有幂等键和审计，不修改旧 Binding/迁移/制品。已有读取和重放语义不变。
5. 运行界面提供历史窗口步数、显式未来路径，未给定值不以 0 静默补全。只有相同 Binding、模型 revision、历史观测、目标/单位和预测时间轴的成功产物才能显示数值差；不同条件路径是条件比较，不是因果效应。
6. 代码阶段标记增至 M9.5/B（0.9.5-b1），不更改 Workflow v1/v2、Provider 模型、Evidence/Release 或 Domain Pack 的旧签名。无数据库迁移和第三方新依赖。

验证采用显式合成资料及真实 API/模型调用，前端组件模拟仅验证交互，不冒充工业或模型 E2E。停在 B，不进入 C 或 M10。

补充：绑定对象选择使用独立最小投影 `/spaces/{id}/binding-entities`，复用 governance.manage 并过滤当前实体版本源密级；不直接扩大 R1 实体/Graph 读取表面，不据此关闭旧 Graph 隔离疑点。

安全校准：真实 Source 失效采用 `source_invalidations` 追加记录，不能检查不存在的 SourceVersion.INVALIDATED 状态来替代。预览/绑定及预测执行前、发布前复用现有失效查询，并拒绝已归档 SourceDocument；不改变 Source 失效契约、旧制品或 Release，仅修复预测适配器遗漏的读取门禁。

既有 API 适配修复：B 真实资料选择验证发现 SourceRepository 将内部 `archived_at` 字段送入禁止额外字段的 SourceDocumentResponse，导致列表/详情/归档响应 500。按原公开契约移除响应投影中的内部字段，数据库归档时间照常保存；不新增 API 字段或修改历史迁移。

同一回归进一步发现详情嵌套版本含内部 `object_key`。详情及归档响应复用公开字段投影，嵌套版本按既有 SourceVersionResponse 投影；内部仓储仍保留读取原始数据所需的存储 key，不向客户端泄露，也不放宽契约。
