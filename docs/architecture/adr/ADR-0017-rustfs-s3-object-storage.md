# ADR-0017: RustFS 作为 S3 兼容对象存储基线

- Status: Accepted
- Approval basis: 用户于 2026-08-24 明确批准“替换为 RustFS，不保留 MinIO”
- Date: 2026-08-24
- Decision owners: 产品负责人、架构负责人
- Related: OQ-INFRA-001, SPK-004, NXW-NFR-AVL-003, NXW-ARCH-001

## Context

R1 需要可私有部署、S3 兼容且可通过 `ObjectStoragePort` 替换的对象存储。原 M0 基线采用的社区项目已归档并明确停止维护，社区发行改为 source-only；历史预编译镜像不再获得更新。M0 为规避已知风险而选用的安全 hotfix 又只有 `linux/amd64`，Apple Silicon 必须模拟运行，形成维护、许可证、供应链和多架构风险。

RustFS 官方仓库持续维护，采用 Apache-2.0，提供 S3 核心能力、单节点模式和 `linux/amd64`/`linux/arm64` 构建路径。当前正式候选版本仍为 RC，官方同时标注分布式模式和生命周期管理仍在测试，因此不能把 M0 启动成功解释为生产成熟性验证。

## Decision question

NEXWEAVE 是否继续保留原对象存储实现，还是在 M0 将活动运行时、健康检查和后续 Adapter 基线完整切换为 RustFS，同时维持厂商无关的 S3/ObjectStorage Port？

## Options

1. 继续使用停止维护的社区发行或自行长期维护源码镜像；
2. 采用非开源免费版或商业发行；
3. 采用 RustFS，并以通用 S3/ObjectStorage Port 隔离实现；
4. 采用 SeaweedFS 或 Ceph RGW。

## Decision

选择 3：

- M0 Compose 固定 RustFS 官方 Quay 多架构索引 `quay.io/rustfs/rustfs:1.0.0-rc.3@sha256:800cf3f352a0a27e3275ca854a51f0027975d7acc7a0d52089a35bcc9fcbf0b5`，不得使用 `latest`；
- 活动代码、配置、健康检查、测试和开发文档不保留旧 Provider、旧凭据或运行时回退；
- 应用层环境变量使用通用 `NEXWEAVE_OBJECT_STORE_*` 命名，Compose 仅在 Adapter 边界映射到 `RUSTFS_*`；
- 领域与公共契约只依赖 `ObjectStoragePort` 和批准的 S3 子集，不依赖 RustFS SDK、管理 API 或磁盘格式；
- M0 只验证真实 RustFS 进程健康与纵向基础设施链路。上传、下载、Range、multipart、checksum、版本控制、预签名 URL、故障恢复和生命周期能力由 SPK-004 及后续对应 Milestone 的真实集成测试验收；
- 不设置原对象存储回退方案。未来替换 RustFS 必须新增 ADR、兼容矩阵、迁移和恢复验证。

## Positive consequences

- 消除停止维护发行、AGPL 义务和单架构旧镜像带来的活动基线风险；
- Apache-2.0 更适合私有化和商业交付，官方构建链覆盖 AMD64/ARM64；
- S3/ObjectStorage Port 保持稳定，业务对象、Raw/Release 和 Evidence 语义不绑定存储厂商；
- M1 尚未实现对象存储 Adapter，现在切换不需要业务 API 或历史对象数据迁移。

## Negative consequences

- RustFS 仍处于 RC，升级节奏、兼容性、漏洞响应和运维经验不如成熟发行稳定；
- 分布式模式和生命周期管理尚不能作为已验收能力；
- RustFS 运行用户为 `10001:10001`，持久卷必须保持该用户可写；已用一次性容器验证镜像声明的 `/data` 卷可由该用户写入；
- S3 兼容必须按 NEXWEAVE 使用子集实测，不能以供应商声明替代证据。

## Migration and compatibility risks

- M0 只使用合成/本地状态，因此没有业务对象迁移；旧本地命名卷不被新服务挂载，也不自动删除。RustFS Compose 已启动并通过健康、S3 子集、重启恢复和逻辑备份恢复验证。
- 已存在的忽略文件 `.env` 需把厂商专用凭据名迁移为通用对象存储凭据名；迁移不得输出或重生成现有密钥。
- 后续禁止依赖 RustFS 管理 API、专有事件、专有元数据或磁盘格式，否则会破坏 S3 Provider 可替换性。
- RustFS 版本升级必须先验证 S3 兼容矩阵、数据升级/回滚、备份恢复、镜像签名、SBOM、CVE 和双架构 digest。

## Validation

M0 通过条件：

1. Compose 解析结果只包含 RustFS 对象存储服务，不存在旧 Provider 服务或凭据；
2. RustFS 使用固定多架构 digest、非 root 运行、随机本地密钥和镜像声明的数据卷；
3. API readiness 返回 `object_storage=up`，Web/验证脚本显示 RustFS/S3；
4. format、lint、typecheck、unit、contract、Web build、secret scan 和 Compose 配置门禁通过；
5. 官方镜像拉取恢复后，完整 Compose、真实健康链路和迁移回滚通过。

生产或承载 Raw/Release 前的附加门禁：SPK-004 形成可复现的 S3 能力、故障恢复、备份恢复、安全扫描和多架构验证报告。

2026-08-24 验证更新：`scripts/verify_rustfs_spk004.py` 在固定镜像上通过单节点 S3/恢复矩阵；对象 key、状态、补偿、受控下载和内部签名镜像规则由 ADR-0018 冻结。GitHub Actions run `32702688049` 已完成双架构 SBOM/CVE/签名权威外部回执。
