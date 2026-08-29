# Infrastructure

M0 的本地开发拓扑由根目录 `compose.yaml` 冻结；本目录保留后续 Compose 模块化、Temporal 配置和可观测性边界，并提供 `fixtures/m0_platform_seed.json` 全合成种子清单。

这些资产仅用于本地工程验证，不代表生产高可用、安全加固或部署认证。

`clamav/` 提供可复现的 M3 ClamAV 运行镜像：基于已锁定摘要的官方 Python/Debian 12 基础镜像，从 Debian 官方安全仓库安装精确版本 `1.4.3+dfsg-1~deb12u2`，启动前以 FreshClam 更新签名，并通过 TCP INSTREAM 暴露给可信协调器。该路径用于规避部分网络环境无法连接 Docker Hub Registry 的问题，不改变 `MalwareScannerPort` 或 fail-closed 策略。
