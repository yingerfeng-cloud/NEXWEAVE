# NEXWEAVE M3 执行与正式验收报告

## 1. 结论

- 阶段：**通过；用户于 2026-08-29 正式验收 M3**。
- 范围：资料中心、不可变 Raw/SourceVersion、版本化解析、SourceAnchor、真实扫描与 Parser 隔离、SourceIngestion v2、API/UI/SDK 和 `0004_m3_source_parsing`。
- 停止边界：M4 仅完成语义模型治理校准，尚未正式下发；本次不实现 Schema、Domain Pack、真实 Compile、Review、Release、Query 或其他后续业务。

## 2. 实际完成范围

- 实现 `SourceDocument`、不可变 `SourceVersion`/Raw 注册、上传会话/批次、`ParseJob`、`DocumentSegment`、`SourceAnchor`、失效与解析失败事实。
- 以 `nexweave.source-ingestion.v2` 执行真实扫描、解析、结果校验、聚合、审计/Outbox 和稳定状态转换；M2 的 `v1` 继续保留为 Kernel Stub/Replay。
- 六类受控适配器通过真实链路：PDF、DOCX、Markdown、TXT、CSV、XLSX。扫描 PDF 在无 OCR Provider 时如实返回 `OCR_REQUIRED/PARTIAL_FAILED`，没有冒充 OCR 成功。
- 可信协调 Activity 与独立、非 root、只读、资源受限且无凭据的 `parser-sandbox` 通过专用内部 IPC 网络协作。

## 3. 验证与证据

- 本地真实 PostgreSQL `0001 → 0004 → 0003 → 0004` 通过，核验 M3 10 张表、6 个数据库保护 trigger 和替代版本唯一性；未修改历史迁移。
- 新建 Temporal v1/v2 history Replay、M3 集成和真实 Compose E2E 通过；`.venv/bin/python scripts/verify_m1.py` 与 `.venv/bin/python scripts/verify_m3.py` 通过。已验收 M2 的归档 history 未取得，因此不声称完成该项证明。
- 本地 ClamAV 真实 clean/EICAR、感染保留与下载拒绝链路通过；本地镜像 Trivy 0.74.0 可修复 HIGH/CRITICAL 为 0。
- GitHub Actions [run 33253911959](https://github.com/yingerfeng-cloud/NEXWEAVE/actions/runs/33253911959) 的 10 个作业全部成功，覆盖质量、Temporal、Compose、应用镜像和 RustFS 审批镜像。远程 amd64/arm64 构建、CycloneDX SBOM、CVE 阻断与 Cosign 签名/验证均通过；[RustFS 证据制品](https://github.com/yingerfeng-cloud/NEXWEAVE/actions/runs/33253911959/artifacts/9715210598) 与 [Web 证据制品](https://github.com/yingerfeng-cloud/NEXWEAVE/actions/runs/33253911959/artifacts/9715213123) 均含双架构 SBOM/漏洞 JSON，两个架构可修复 HIGH/CRITICAL 均为 0。
- 远程 `main` 当前 M3 供应链收尾提交为 [`bd896ac4e85b6a47e7e4eae97bd836803da2c204`](https://github.com/yingerfeng-cloud/NEXWEAVE/commit/bd896ac4e85b6a47e7e4eae97bd836803da2c204)。

## 4. 安全、迁移与需求追踪

- 无真实凭据、客户资料或未脱敏日志进入 M3 交付；运行时凭据仅通过环境变量名/Secret 引用读取。
- `0004_m3_source_parsing` 为追加式迁移；未覆盖或回写 `0001`—`0003`，一次性数据库仅用于升级/回滚验证。
- `NXW-SOURCE-001`、`NXW-SOURCE-002` 已在需求追踪矩阵标记为 `VERIFIED；M3 USER ACCEPTED`。M2 Kernel Stub 不作为 M3 业务证据。

## 5. 遗留项与停止声明

- 未配置真实 OCR Provider；扫描 PDF 继续如实报告 `OCR_REQUIRED/PARTIAL`。
- 已验收 M2 归档 Temporal history Replay 尚未取得；生产 HA/DR、生产 OIDC/Secret Provider/HTTPS、容量性能和国产浏览器认证属于后续门禁。
- **M3 已正式验收并停止。除非用户另行明确下发，不进入 M4 实现。**
