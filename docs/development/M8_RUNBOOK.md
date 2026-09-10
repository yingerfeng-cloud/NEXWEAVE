# NEXWEAVE M8 Runbook

M8 enables read-only Connector synchronization and Obsidian Markdown exchange. GridCrew integration is deliberately deferred: there are no GridCrew endpoints, webhook deliveries, Skill bindings or GridCrew SDK claims in this runbook.

## Safety boundary

- Create a governed `ConnectorDefinition` first, then create a `ConnectorInstance` with a non-secret `CredentialRef` and explicit allowlist.
- All connector types are read-only. `FILESYSTEM` and `GIT` accept only allowlisted local paths; `S3` accepts only the configured development object store prefix; `WEB_REST` permits only explicit HTTP(S) prefixes and rejects redirects.
- A sync writes immutable Raw bytes, then creates a normal `SourceVersion` and M3 parse workflow. It never creates a Claim, Wiki page or Release directly.
- Obsidian export writes immutable page/base/checksum metadata in YAML frontmatter. A return import is a draft or a recorded conflict; it cannot update Release, Evidence, permission, classification or a stable page identifier.
- 页面知识图谱是 NEXWEAVE 内置的只读 Wiki 导航投影：它从页面链接与 backlinks 读取节点和边，不读取本机 Obsidian Vault，也不表示 Release、Evidence 或已审核结论。

## Wiki 双向链接知识图谱

1. 在“知识图谱”打开页面图谱。节点按 Wiki 模板着色，箭头表示原始页面出链；沿反方向可达的边就是反向引用。
2. 使用搜索或页面类型过滤；滚轮缩放、拖拽平移，悬停高亮关联路径。点击任一节点可在受限范围内聚焦其最多两跳的出链和反向引用，再从侧栏沿链接继续聚焦或打开对应 Wiki 页面。
3. 图谱响应受 `page.read`、空间/租户隔离、1—3 跳和 10—500 节点上限保护。出现“达到安全显示上限”时，使用节点聚焦，不得将屏幕上的局部图误作全量。

## Local verification

1. Apply `0009_m8_connector_obsidian` after the M7 head.
2. Register a `FILESYSTEM` ConnectorInstance that allowlists one test directory and points to a supported document within it.
3. Start a sync and follow its `workflow_id`; verify a new SourceVersion and ParseJob are created.
4. Export a current Wiki page, edit only the Markdown body and import it back. Verify an `EDITING` page version/draft record is created. Change the base version or frontmatter checksum and verify a conflict record is returned instead.

Production rollout still requires an external Secret Provider, OIDC, per-target network approval and real environment E2E. Do not add any GridCrew implementation without a separate user dispatch and integration decision.
