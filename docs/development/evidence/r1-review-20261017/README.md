# R1 Review A 批技术证据

本目录是 2026-10-17 新执行证据。输入材料与过去验收记录均不作为本次通过结果。
执行范围、兼容性和限制见 [A 批执行报告](../../reports/R1_Review_A批执行报告_20261017.md)。

| 文件 | 层级与用途 |
|---|---|
| `baseline-security-observations.log` | 只读基线副本运行附件原探针；使用替身连接/repository。2 passed 证明旧缺陷被观察，不能计作修复通过 |
| `quality.log` | 当前源码完整 make check；包含故意触发失败状态的组件测试 stderr，整体退出 0 |
| `database.log` | 完整迁移 PostgreSQL + 实际鉴权 ASGI 路由；13 个合成技术回归通过。不是 Web 作者/审核验收 |
| `migrations.log` | 一次性数据库升级/回退/再升级；未迁移用户生产库 |
| `real-r1-chain.log` | 实际 HTTP/S3/ClamAV/Temporal/worker 技术链路；合成资料、开发模型，经 API 完成业务步骤 |
| `review-outage.log` | 真实停止/恢复隔离 Temporal 的五段投递演练；无强写成功状态 |
| `legacy-gates.log` | 当前 CI 要求的 M1—M4 实际集成，包括 worker 重启/回放 |
| `temporal-activity-substitutes.log` | 实际 Temporal，替身 Activity，仅验证工作流逻辑 |
| `verification.json` | 实际计数、未执行门禁、七镜像 ID/审计时间/原 JSON 哈希；无原始凭据或内部服务地址 |
| `browser-supported.png` | 实际 Web 提问得到冻结知识范围内有引用答案 |
| `browser-source.png` | 实际点击引用打开原文定位 |
| `browser-refused.png` | 实际错误对象问题得到证据不足拒答 |

日志中的本机绝对路径替换为 `<REPO>` / `<TMP>`，保留结果和警告。原镜像扫描 JSON
含本机镜像元数据，留在 ignored `.nexweave-data/r1-review-20261017/`，本目录只保存可核对哈希与摘要。
扫描沿用“可修复 HIGH/CRITICAL”门槛，不意味着不存在其他级别或无修复的漏洞。
没有远端 CI、AMD64 签名/晋级、外部 IAM、语义模型或工业效果通过证据。

浏览器截图仅证明问答/原文/拒答路径。审核、裁决和发布由合成 API 技术流程执行，
尚不能证明用户从新空间仅经 Web 完成全部核心验收场景。
