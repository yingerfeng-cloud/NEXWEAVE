# Architecture Decision Records

ADR-0001—0018 已在 M0 冻结；ADR-0019 冻结 M1；ADR-0020 冻结 M2 Temporal 内核；ADR-0021 冻结 M3 Source/Parse；ADR-0022/0023 冻结 M4 语义模型治理与实现级契约；ADR-0024 冻结 M5 Compile/Wiki/Model Gateway；ADR-0025 冻结 M6 Claim/Evidence、冲突与人工审核；ADR-0026 冻结 M7 质量、发布与查询投影；ADR-0027 冻结 M8 只读 Connector 与 Obsidian 草稿回导边界；ADR-0028 冻结 M8 Wiki 双向链接图谱投影；ADR-0029 冻结 M9 Equipment RCA Pack 与真实试点证据边界；ADR-0030 建立 M9 公开候选语料并将 GridCrew 联合试点延期。被替代时必须保留历史并链接 superseding ADR。

| ADR | 主题 | 状态 |
|---|---|---|
| ADR-0001 | NEXWEAVE 独立产品与 GridCrew API 集成 | Accepted |
| ADR-0002 | Monorepo、模块化单体与独立 Worker | Accepted |
| ADR-0003 | Python/FastAPI 产品核心 | Accepted |
| ADR-0004 | Temporal 可靠知识工作流 | Accepted |
| ADR-0005 | PostgreSQL + pgvector R1 数据基座 | Accepted |
| ADR-0006 | 关系表优先、图数据库后置 | Accepted |
| ADR-0007 | 数据库权威、Markdown 可交换表示 | Accepted |
| ADR-0008 | Raw/Draft/Release 分层与不可变 Release | Accepted |
| ADR-0009 | Domain Pack 声明式扩展 | Accepted |
| ADR-0010 | Model Gateway 与 Connector SPI | Accepted |
| ADR-0011 | GridCrew Knowledge Pack → Skill 映射 | Accepted |
| ADR-0012 | 企业 Java/CUD4.0 适配壳 | Accepted |
| ADR-0013 | 标识、租户隔离与通用元数据 | Accepted |
| ADR-0014 | SourceAnchor、Evidence 与 Citation | Accepted |
| ADR-0015 | 公共契约、错误、权限与数据密级 | Accepted |
| ADR-0016 | Release、幂等、事件与状态投影 | Accepted |
| ADR-0017 | RustFS S3 兼容对象存储基线 | Accepted |
| ADR-0018 | SourceVersion Raw 对象与容器供应链门禁 | Accepted |
| ADR-0019 | M1 身份、授权、空间与托管对象基础 | Accepted |
| ADR-0020 | M2 Temporal 内核、任务投影与控制契约 | Accepted |
| ADR-0021 | M3 Source、解析版本与 SourceAnchor 语义 | Accepted |
| ADR-0022 | M4 语义模型、SchemaVersion 权威与 Domain Pack 组合 | Accepted |
| ADR-0023 | M4 Pack 实现契约——稳定 key、规范格式、签名、迁移与 UI | Accepted |
| ADR-0024 | M5 Compile、Wiki 与 Model Gateway 实现契约 | Accepted |
| ADR-0025 | M6 Claim、Evidence、冲突与人工审核实现契约 | Accepted |
| ADR-0026 | M7 质量门禁、不可变发布与固定版本查询投影 | Accepted |
| ADR-0027 | M8 只读 Connector 与 Obsidian 草稿回导边界 | Accepted |
| ADR-0028 | M8 Wiki 双向链接知识图谱投影 | Accepted |
| ADR-0029 | M9 Equipment RCA Pack 与联合试点边界 | Accepted |
| ADR-0030 | M9 公开 RCA 候选语料与 GridCrew 联合试点延期 | Accepted |
| ADR-0034 | 阶段 B 自主绑定、受控预检与同窗口场景比较 | Accepted under explicit Stage B authorization |
| ADR-0035 | 阶段 C 固定 Release 知识回接与当前引用门禁 | Accepted under explicit Stage C authorization |

ADR-0036：[阶段 D 固定发布读取与验收收口](ADR-0036-stage-d-trusted-read-boundary.md)，Accepted，实施与本地技术验证完成（2026-09-10）；不进入 M10。
