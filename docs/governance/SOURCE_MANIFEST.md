# Source Manifest

> 盘点日期：2026-08-23  
> 原始交付包保持不变；`docs/` 下副本用于治理和后续开发读取，发生批准修订时必须链接 ADR，不能继续冒充原始哈希内容。

## NEXWEAVE 上位资料

| 文件 | SHA-256 | 仓库位置 | 状态 |
|---|---|---|---|
| PRD V1.0 | `314dbe1ea014a2f5847c141ed6550b5b57e5cd3aad83cceea071c50ed94e24ac` | `docs/product/nexweave/NEXWEAVE_LLM_Wiki标准化平台_PRD_V1.0.md` | 已归档 |
| 高保真原型 V1.0 | `f6a887f8ff5de57c2ee5afe1fe8328d384fe7856d94549ebeaba5bdb9fcd64aa` | `docs/product/nexweave/NEXWEAVE_高保真交互原型_V1.0.html` | 已归档；静态演示 |
| 交付说明 | `d3836c481dfb0085ea658c6b79b8da259bea4e7f58ac103a3c4b07209d5ca10b` | `docs/product/nexweave/README_交付说明.md` | 已归档 |
| 完整开发总纲 V1.0 | `91696d601e089eab5e8b35ad2e43878e266eb715a5aac62eeba9d3b2540b40b2` | `NEXWEAVE_完整分阶段开发任务书_V1.0/00_NEXWEAVE_完整分阶段开发任务总纲_V1.0.md` | 原始归档；哈希于 2026-08-24 复核一致 |
| M-1 任务书 | `b55b5d41a1fcc54956edd13d18ee24bc295b57a9610dbda34700b8ce41edbd86` | `NEXWEAVE_完整分阶段开发任务书_V1.0/01_NEXWEAVE_M-1_编码前启动准备与治理基线建立任务书.md` | 原始归档；哈希于 2026-08-24 复核一致；M-1 已验收 |
| 原型总览 PNG | — | — | 交付说明列出但源包缺失 |
| Schema PNG | — | — | 交付说明列出但源包缺失 |

`docs/development/tasks/` 是受治理执行副本。用户于 2026-08-24 批准 ADR-0017 后，该副本中的 M0—M15、总纲、M0-Lite 和执行说明已把对象存储活动基线修订为 RustFS/S3；已验收的 M-1 副本与根目录原始交付包保持原文。修订不改变上表原始文件哈希。

## GridCrew 参考资料

来源为相邻 `GridCrew` 项目的只读副本，归档了：产品路线/开发计划 DOCX、统一命名、M-1 任务与报告、架构基线、领域模型、事件、安全、开放问题和与执行/网关/多租户/Evidence/版本相关 ADR。

GridCrew 当前状态为 M-1C 完成、M0 未开始、Git 身份待配置。GridCrew 资料只用于兼容共享架构原则，不成为 NEXWEAVE 产品权威源。

## 领域资料

`docs/reference/domain/rca/` 当前只有缺失说明。任何后续真实资料必须完成授权、脱敏、密级、用途、保留期限和模型出域审查后再归档。
