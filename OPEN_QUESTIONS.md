# NEXWEAVE Open Questions

> 状态值：`OPEN`、`PROPOSED`、`DECIDED`、`DEFERRED`。  
> M2 已正式验收。用户已正式下发 M3，任务书、ADR 与治理校准已完成并进入正式实施；任何仍未决事项不得被编码静默固化。

## 已明确

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-REL-001 | DECIDED | 当前 Release 统一采用 R1=M0—M9、R2=M10—M12、R3=M13—M15 | 用户 2026-08-23 明确“统一”；完整开发总纲 |
| OQ-PROD-001 | DECIDED | NEXWEAVE 是独立产品，GridCrew 通过 API/事件/SDK 集成 | PRD、M-1、GridCrew 基线一致 |
| OQ-DOMAIN-001 | DECIDED | Equipment RCA 是 Domain Pack，不进入平台核心 | PRD、M-1、总纲一致 |
| OQ-GOV-001 | DECIDED | M-1 治理基线正式验收通过；M0 需单独下发 | 用户 2026-08-23 明确验收通过 |
| OQ-GOV-002 | DECIDED | 进入正式 M0，不执行 M0-Lite；完成后停止在 M0 边界 | 用户 2026-08-23 明确下发“请进入M0” |
| OQ-GOV-003 | DECIDED | M0 正式验收通过；已披露的外部 CI、容器供应链与 RustFS SPK-004 风险作为 P1 继续跟踪，M1 必须另行明确下发 | 用户 2026-08-24 明确“同意M0验收”；M0 执行报告 |
| OQ-GOV-004 | DECIDED | 上述 M0 P1 已通过远程 main CI、双架构 SBOM/CVE/Cosign 与 SPK-004 实测闭环；RustFS RC 的 HA/DR/升级规模风险转入既定 M7/M12 门禁，不再是 M0 阻塞 | 用户 2026-08-24 要求解决剩余问题；ADR-0018；GitHub Actions run 32702688049 |
| OQ-GOV-005 | DECIDED | 正式进入 M1，以 `03_NEXWEAVE_M1_平台基础、身份权限与核心领域模型任务书.md` 为边界，完成后停止 | 用户 2026-08-24 明确下发“进入 M1” |
| OQ-GOV-006 | DECIDED | M1 正式验收通过并进入 M2，以 `04_NEXWEAVE_M2_Temporal可靠知识工作流内核任务书.md` 为边界，完成后停止 | 用户 2026-08-24 明确“同意 M1 验收，进入 M2” |
| OQ-GOV-007 | DECIDED | M2 正式验收通过；用户正式下发 M3，并明确授权按 M0—M2 已验收基线完成任务书/ADR/治理校准后继续正式实施，实施后进行独立审查并停止在 M3 | 用户 2026-08-25 明确 M2 验收与 M3 下发/实施/审查顺序 |

## M3 已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-PARSE-001 | DECIDED | 每次 reparse 创建新 ParseJob/Workflow；retry 保持同一输入配置；部分成功为 `PARTIAL_FAILED/PARTIAL` 并列出失败单元；reparse 失败不破坏既有 active 结果；文件替代创建新 SourceVersion；Anchor 固定 SourceVersion + checksum + ParseJob，重定位新建 Anchor；M2 v1 Stub 保留 Replay，M3 使用 v2。无真实 OCR Provider 时扫描 PDF 必须真实检测并明确 `OCR_REQUIRED`，不得冒充 OCR 成功 | ADR-0021；ADR-0008、0014、0018、0020；M3 正式任务书校准 |

## M3 实施中发现的权威冲突

| ID | 状态 | 问题 | 处理边界 |
|---|---|---|---|
| OQ-M3-ANCHOR-001 | DECIDED | `docs/architecture/DATA_MODEL_BASELINE.md` 第 6 节曾把 Anchor 失效结果写为 `STALE/INVALID`，与 ADR-0021 明确限定的 `VALID/STALE/UNRESOLVED/REVOKED` 及“不得使用 `INVALID`”冲突；已确认为低优先级基线残留并修正为 `STALE/UNRESOLVED/REVOKED`，不得实现 `INVALID` | M3 正式任务书；Accepted ADR-0021；主执行者 2026-08-25 按权威优先级确认并要求保留发现/修正证据 |

## M0 已冻结决策

| ID | 状态 | 决策 | 依据 |
|---|---|---|---|
| OQ-TECH-001 | DECIDED | 产品核心采用 Python 3.12/FastAPI；Java/CUD4.0 仅作企业适配壳 | M0 任务书 Python/TypeScript Monorepo 要求；ADR-0003、ADR-0012 |
| OQ-EXEC-001 | DECIDED | Temporal 是长任务执行权威；数据库保存业务事实与查询投影 | M0 任务书；ADR-0004 |
| OQ-IAM-001 | DECIDED | 与 GridCrew 仅保持 OIDC/服务身份协议兼容，可复用提供方但独立部署与数据 | 独立产品边界；ADR-0001、ADR-0015 |
| OQ-GW-001 | DECIDED | Model Gateway、Connector、Artifact/Evidence 先冻结兼容契约；服务复用不得改变独立权限和可用性边界 | ADR-0005、ADR-0010 |
| OQ-SOURCE-001 | DECIDED | SourceAnchor 采用绑定 SourceVersion 与 checksum 的版本化复合定位器，并含 excerpt hash 与定位状态 | ADR-0014 |
| OQ-SCHEMA-001 | DECIDED | 破坏性变更不修改历史 Release；草稿迁移形成新对象版本和影响报告 | ADR-0008、ADR-0016 |
| OQ-PACK-001 | DECIDED | 安装记录/版本不可变；卸载只禁用不删知识；升级必须显式迁移且可回滚 | ADR-0009 |
| OQ-QUERY-001 | DECIDED | R1 Query 每次只绑定一个空间内的固定 Release | ADR-0008、ADR-0016 |
| OQ-SEC-001 | DECIDED | 四级密级 PUBLIC/INTERNAL/CONFIDENTIAL/HIGHLY_RESTRICTED；最高密级禁止外部模型出域 | ADR-0015 |
| OQ-TENANT-001 | DECIDED | 从基础表开始保留 tenant_id/space_id；R1 必须验证跨租户阻断 | ADR-0013 |
| OQ-INFRA-001 | DECIDED | M0 用本机 Docker Compose 联调 PostgreSQL、RustFS、Redis、Temporal、API、Worker、Web；对象存储保持 S3/ObjectStorage Port 边界且不设置旧 Provider 回退 | 用户 2026-08-24 明确批准；ADR-0017；仅为开发基线 |
| OQ-EVID-001 | DECIDED | Claim、Relation、Evidence、Citation 分离：事实表达、结构关系、证据记录和回答引用各自独立 | ADR-0014 |
| OQ-MARKDOWN-001 | DECIDED | Markdown/Git 只作交换、展示与导出，数据库/Release 是权威状态 | ADR-0003 |
| OQ-SEARCH-001 | DECIDED | R1 默认 PostgreSQL FTS + pgvector + Relation；增加专用引擎须以测量证据和 ADR 触发 | ADR-0002 |
| OQ-RELEASE-001 | DECIDED | 空间内 SemVer + 不可变 manifest + channel pointer；回滚移动指针，不改历史版本 | ADR-0008、ADR-0016 |
| OQ-DAMENG-001 | DECIDED | 达梦/CUD4.0/国产中间件是后续适配壳，不形成第二产品核心 | ADR-0001 |

## M0 未代替业务负责人决定的事项

| ID | 状态 | 问题 | 处理边界 |
|---|---|---|---|
| OQ-METRIC-001 | DEFERRED | R1 试点引用准确率、问题覆盖率、专家接受率阈值是多少？ | 不伪造阈值；M5 前形成测量方案，M9 试点前由产品/RCA 专家批准 |
| OQ-SEC-CONTACT-001 | OPEN | 私密安全漏洞的报告联系人和响应 SLA？ | M0 可建立无联系人占位的安全流程，公开/交付前必须由安全负责人补齐 |
| OQ-LICENSE-001 | OPEN | NEXWEAVE 源代码与分发许可证采用什么策略？ | 未决定前不声明开源许可、不对外分发 |
| OQ-INFRA-002 | DECIDED | 开发机使用 Veee 全局模式恢复 Docker daemon 对 Docker Hub 官方 Registry 的访问，不引入镜像站或非官方替代源 | 用户 2026-08-24 调整网络模式；pgvector、Redis、Temporal、Python、Node、Nginx 官方镜像均已成功拉取，项目镜像构建成功；首次认证请求仍有一次 IPv6 超时，后续重试成功，继续观察稳定性 |

## P1：对应能力编码前必须决定

| ID | 状态 | 问题 | 最晚阶段 |
|---|---|---|---|
| OQ-PACK-UI-001 | OPEN | Domain Pack 是否允许前端扩展，允许到声明式布局还是沙箱组件？ | M4 |
| OQ-GRID-001 | OPEN | GridCrew Skill 如何锁定空间、Release、权限策略和租户映射？ | M8 前联合冻结 |
| OQ-OBSIDIAN-001 | OPEN | Obsidian 导入、导出、稳定 ID 和冲突回写策略？ | M8 |
| OQ-REVIEW-001 | OPEN | 风险等级、职责分离、批量审核和超时升级策略由谁配置？ | M6 |
| OQ-CONNECTOR-001 | OPEN | 首批文件/S3/Web/Git 连接器的授权和网络白名单？ | M8 |
| OQ-RCA-001 | OPEN | 合规脱敏 RCA 数据、专家名单、标准问题集和试点设备范围？ | M9 前，宜 M0 启动 |

## P2：可后置但需记录

| ID | 状态 | 问题 | 计划 |
|---|---|---|---|
| OQ-PREVIEW-001 | OPEN | 原交付说明列出的两张 PNG 预览图缺失，是否补齐？ | 不阻塞 M0，补资料包完整性 |
| OQ-MANIFEST-001 | OPEN | 原 manifest 未列出嵌套 PRD/原型文件，是否升级交付清单？ | 不改原包，在仓库 SOURCE_MANIFEST 补齐 |

## 决策记录规则

每个 `DECIDED` 项必须关联批准人、日期、ADR/会议记录和影响范围。若决策改变对象、状态、版本、API、事件、Workflow、SourceAnchor 或 Release 语义，必须通过 ADR，而不能只改本表。
