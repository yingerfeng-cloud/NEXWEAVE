# ADR-0018: SourceVersion Raw 对象与容器供应链门禁

- Status: Accepted
- Approval basis: 用户于 2026-08-24 要求解决 M0 剩余 RustFS SPK-004 与容器供应链 P1
- Date: 2026-08-24
- Decision owners: 产品负责人、架构负责人
- Related: ADR-0008, ADR-0017, SPK-004, NXW-NFR-AVL-003, NXW-NFR-SEC-003

## Context

ADR-0017 已选择 RustFS/S3，但尚未固定 SourceVersion Raw 对象的不可变写入规则，也没有完成 SBOM、CVE 和签名回执。旧领域模型页还残留 `UPLOADING/SCANNING/READY`，与已接受的统一 SourceVersion 状态 `STORED/PARSING/PARTIAL/PARSED/FAILED/SUPERSEDED` 冲突。RustFS 固定 Quay 索引虽有双架构 manifest，却没有 Cosign 可发现的上游签名或 SBOM，不能把“有 attestation manifest”解释为已经通过供应链验证。

## Decision

### Raw 对象与一致性

- canonical key 采用 `raw/v1/{tenant_id}/{space_id}/{source_document_id}/{source_version_id}/{sha256}`；ID 使用规范小写 UUID，SHA-256 使用 64 位小写十六进制；原始文件名只保存在受控数据库元数据中，不进入 key；
- SourceVersion ID 在开始上传前分配。单次 PUT 和 multipart complete 都必须使用 `If-None-Match: *` 或等价条件写；桶版本控制作为纵深防御，不能替代应用层不可变约束；
- 客户端声明的大小、MIME 和 checksum 不可信。完成上传后由 Activity 重新读取对象元数据/内容校验 SHA-256，再以事务写入 SourceVersion、审计与 Outbox；不一致时保留隔离对象供受控清理，不登记为可解析版本；
- 同一幂等键且请求哈希/checksum 相同返回原结果；同一幂等键携带不同内容返回 `IDEMPOTENCY_KEY_REUSED`；相同字节出现在不同业务文档时只提示，不跨 tenant/space 或业务对象静默合并；
- 替代资料总是创建新的 SourceVersion ID、key 和 checksum，并通过关系标记旧版本 `SUPERSEDED`，不原地覆盖；
- 下载必须先由 API 重新执行 tenant、space、对象状态和密级授权，再签发短期、限定 method/key 的预签名 URL；桶和对象保持私有，客户端不得持有长期 S3 凭据。

### 状态、失败与补偿

- 上传会话使用独立技术状态 `INITIATED/UPLOADING/COMPLETING/COMPLETED/ABORTED/EXPIRED`，不扩展 SourceVersion 聚合状态；
- SourceVersion 只使用已接受状态。对象持久化并校验后进入 `STORED`；恶意文件扫描是 SourceIngestion Workflow/Activity 门禁，扫描失败进入 `FAILED` 并禁止解析；通过后才能进入 `PARSING`；
- 传输超时、5xx 和短暂依赖故障可按相同 upload/part 幂等重试；checksum 不一致、条件写冲突、权限拒绝和恶意内容不可原样自动重试；
- multipart 失败必须 abort；数据库事务失败后的已校验孤儿对象由带审计的补偿任务按 key/checksum 对账，禁止后台任务直接推进业务状态；取消和失效不物理删除已登记 Raw。

### 备份与恢复

- Provider-neutral 备份以版本化对象清单为权威，清单至少包含 tenant/space、key、version ID、size、SHA-256、classification 和备份时间；恢复后逐对象重新计算 checksum；
- M0/SPK-004 的逻辑复制与容器重启验证只证明单节点、S3 子集的数据可恢复性，不代表多节点一致性、RPO/RTO 或生产灾备已经验收；这些仍由 M7/M12 的数据规模、故障注入和运维演练验证。

### 容器供应链

- CI 在主分支构建 API、Worker、Web 的 `linux/amd64` 与 `linux/arm64` 镜像，生成 CycloneDX SBOM，使用固定 Trivy 版本阻断所有“已有修复版本”的 HIGH/CRITICAL 漏洞，并通过 GitHub OIDC/Cosign 对不可变 digest 签名；
- RustFS 候选镜像只能从 ADR-0017 固定的 Quay index digest 原样复制；CI 必须确认目标 digest 不变、双架构存在、两种架构的 SBOM/CVE 门禁通过，才能签名并添加 `1.0.0-rc.3-approved` 标签；
- 该签名表示 NEXWEAVE 对精确上游字节的内部准入，不是 RustFS 上游发布者签名，也不能补造上游 provenance；运行时和发布系统必须按 digest 验证 NEXWEAVE CI 身份，不能只信任可变标签；
- M0 本地 Compose 继续使用官方 Quay digest，避免把本地开发绑定到私有制品库。生产/试点推广使用经签名的批准镜像，并保留 SBOM、漏洞报告、签名验证和 CI run 证据。

## Consequences

- Raw First、不静默覆盖、重新授权下载与 Provider 可替换性得到可执行约束；
- 上传/扫描的技术执行状态不再与 SourceVersion 业务状态冲突；
- 高危漏洞扫描会随数据库更新而使 CI 失败，这是预期的发布阻断；例外必须有期限、影响分析、负责人和单独批准，不得用全局 ignore 隐藏；
- RustFS 仍是 RC。SPK-004 通过不等于分布式、HA、升级回滚或规模生产成熟，相关声明继续受后续 Milestone 门禁约束。

## Validation

- `make rustfs-spike` 在真实 Compose RustFS 上验证 PUT/GET/HEAD/list、Range、checksum、条件写、版本、预签名、鉴权、multipart 重试/abort、生命周期、重启恢复和逻辑备份恢复；
- GitHub 主分支 CI 生成并保存四类镜像的双架构 SBOM/CVE 证据，对发布 digest 进行 Cosign 签名与身份验证；
- M1/M3 实现 SourceVersion/ObjectStorage Adapter 时，须将上述 key、幂等、状态、授权和补偿规则写入契约与真实集成测试，不得在 M0 用 Mock 冒充业务功能。
