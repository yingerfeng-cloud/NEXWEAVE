# ADR-0027: M8 只读 Connector 与 Obsidian 草稿回导边界

- Status: Accepted
- Date: 2026-08-31
- Approval basis: 用户正式下发 M8，并确认保守 Connector/Obsidian 默认；GridCrew 集成延期
- Decision owners: 产品、架构、安全负责人
- Related: NXW-INTEGRATION-001, NXW-NFR-SEC-003, NXW-SOURCE-001, NXW-WIKI-001

## Context

M8 需要把受控外部资料转化为可追溯的 `SourceVersion`，同时允许专家使用 Obsidian 编辑交换副本。此前 Connector 授权、出站网络、Obsidian 稳定身份和回导冲突语义未冻结；GridCrew 尚处规划期，当前没有可安全联调的对端。

## Decision

1. 首期 Connector 只读。仅支持受控本地目录、开发 RustFS/S3、Mock REST 与本地 Git 仓库；所有实际外部地址、目录根、S3 endpoint、仓库 URL 和端口必须逐 `ConnectorInstance` 显式 allowlist。未配置目标一律拒绝，禁止私网探测、重定向跳转、任意路径访问和写回外部系统。
2. 凭据永不进入 API 请求日志、数据库明文、任务输入或前端。配置只保存受审计 `CredentialRef`；首期测试 Provider 仅解析命名引用，生产仍须部署外部 Secret Provider。各 Connector 使用最小权限的独立只读服务身份。
3. `ConnectorDefinition` 描述能力，`ConnectorInstance` 固定类型、受控配置、allowlist 与字段映射版本；`SyncRun` 固定开始/结束 Watermark、输入配置 checksum、结果与 Workflow。同步把原始字节通过既有受控 Source upload/scan/Raw/version 流程写入，不能直接生成 Claim、Wiki 或 Release。
4. Obsidian 导出采用 Markdown/YAML frontmatter，包含不可变 `nexweave_page_id`、导出基线版本、固定 Release（如有）和内容 checksum。文件改名/移动不改变身份。没有有效 ID 的文件只能形成新草稿候选，不能匹配或修改既有页面。
5. Obsidian 回导执行三方 diff（导出基线、当前 NEXWEAVE 页面版本、回导文件）。回导始终创建草稿/审核输入；基线漂移、ID/保护区/安全元数据篡改或重叠内容变更生成显式 Conflict，绝不覆盖当前页面或 Release。密级、权限、Evidence、Release 与稳定 ID 不可由 Obsidian 回导修改。
6. GridCrew Knowledge API、Skill 映射、Webhook、服务身份映射和 GridCrew SDK 作为规划期延后项。本 ADR 不实现它们，也不改变 ADR-0001/0011 的独立部署和固定 Release 边界。

## Compatibility and migration

- 新增 additive `0009_m8_connector_obsidian`，不修改历史迁移。M1 的 `ConnectorDefinition` 配置事实保持兼容。
- M8 的同步结果复用 M3 Source/Raw/Parse 与 M5 Wiki 草稿语义；不更改已发布 Release、Evidence 或 SourceAnchor 的事实语义。
- 发布事件继续保留 M7 transactional outbox；M8 不向 GridCrew 投递。

## Validation

- 单元/契约：allowlist、只读类型、凭据脱敏、Watermark 幂等、Source 输入、Obsidian stable ID、三方 diff 和冲突规则。
- 集成/E2E：本地受限目录或 mock connector 到 SourceVersion/Parse 的真实链路；Obsidian 导出、无冲突草稿回导和冲突回导均不修改 Release。
