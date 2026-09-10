# M9 公开 RCA 技术试点运行证据

> 运行日期：2026-09-02  
> 性质：真实公开资料、本地技术试点；不是专家评审、客户适配或 Knowledge Release 证据  
> 验证入口：修复后的 Web/API 路径与隔离本地租户

## 1. 运行边界

- 资料：NTSB-MIR-22-06、NTSB-AAR-18-01、NTSB-PIR-22-02、NTSB-RIR-24-05。
- 原 PDF 均保留为不可变 Raw SourceVersion；文件带 PDF 加密标志，解析器按安全策略拒绝直接解析并留下 `FAILED` 审计。
- 仅文本派生件在内存中生成，逐份排除 admission manifest 的 `excludedVisualPages`，再作为独立 SourceVersion 解析。
- ModelProfile 为 `nexweave.local-structured/1`，`external_llm_called=false`、估算成本为 0；不把本地确定性编译器描述为外部 LLM 或 RCA 专家。
- 运行强制停在候选态：正式 Claim、ReviewCase 和 Release 均为 0。

## 2. Pack 与 Schema 证据

| 对象 | 运行事实 |
|---|---|
| 隔离试点空间 | `01a060fa-1c1f-7280-a63e-0d4512284ceb` / `m9-public-pilot-ac877b1f47` |
| core-pack | `01a060f3-b8a0-7698-a9cb-31bed13e736a` / `core-pack@1.0.0` |
| Equipment RCA Pack | `01a060f3-b8b3-7bd1-afc8-17007b6aa4b0` / `equipment-rca-pack@1.0.0` / `sha256:a760fe3a41f64b0f6f35135c29363ad275441c4e51369f50bb8089bcbe68934d` |
| Pack Installation | `01a060fa-1c2d-7a17-be4a-023b4a9cffaa` / `ACTIVE` |
| PUBLISHED SchemaVersion | `01a060fa-1c73-7a05-907c-fed9722d0aa0` |
| composition checksum | `sha256:5ccbf47f553d31d97857fe23c1a22f654ea49ca76e3ace372466756be2b6891e` |

真实 Pack 首次安装暴露 M4 持久化与 M7 `evaluation_suites.created_by NOT NULL` 的兼容缺陷。修复后增加回归测试，重建 Worker，再次安装达到 `ACTIVE`；没有清库、删除历史 Pack 或修改历史迁移。

## 3. Source 与 Compile 证据

| 来源 | Raw SourceVersion / Parse | 文本 SourceVersion / Parse | CompileJob | ClaimCandidate | EvidenceCandidate | RelationCandidate |
|---|---|---|---|---:|---:|---:|
| NTSB-MIR-22-06 | `01a060fa-1d8a-7190-9ae8-7e8625f1c532` / `FAILED` | `01a060fa-1f7d-7b88-ba6d-2215d04cf8a0` / `SUCCEEDED` | `01a060fa-370b-7515-b45a-594b1d5e4c0c` | 4 | 4 | 0 |
| NTSB-AAR-18-01 | `01a060fa-20c3-7f32-92c1-47d91f59bdec` / `FAILED` | `01a060fa-25e0-718c-85c5-424f2ee6def5` / `SUCCEEDED` | `01a060fa-382c-71a5-8714-80d4d10029ed` | 101 | 103 | 2 |
| NTSB-PIR-22-02 | `01a060fa-2737-7b0f-8c52-6e6ec11c999d` / `FAILED` | `01a060fa-2a88-78d1-a5c5-c6fd261276e5` / `SUCCEEDED` | `01a060fa-3a62-7de3-a80d-c737f94cf25b` | 60 | 63 | 3 |
| NTSB-RIR-24-05 | `01a060fa-2bcb-7b48-8dc2-dcdea71ec768` / `FAILED` | `01a060fa-34b6-7f02-90b7-c79713504427` / `SUCCEEDED` | `01a060fa-3b80-7a29-8d6e-84f534a352f0` | 203 | 207 | 4 |

合计：368 个 ClaimCandidate、377 个 EvidenceCandidate、9 个 RelationCandidate。四个 Raw 解析失败、四个派生解析成功、四个 Compile 执行成功均存在相应审计记录。

## 4. 同轮修复与验证

- Web Nginx `client_max_body_size` 从默认 1 MB 校准为 100 MB，与 API 默认受控上限一致；最大 6,559,547 bytes 的报告经 `:8080` 上传，不再返回 413。
- API 仍校验声明大小、实际 body 长度、checksum、ClamAV 和 Source 内容类型；提高代理上限没有绕过应用门禁。
- `evaluation_suites` Pack 持久化补齐 `created_by`，与 M7 非空约束一致。
- 定向回归：Ruff、mypy、12 项 Pack/API 测试通过；最终端到端脚本通过。

## 5. 未关闭的外部 P0

- 具备签署权限的 RCA 专家身份与职责分离名单；
- 经产品/RCA 专家批准的引用准确率、覆盖率、接受率、修改比例等阈值；
- 对 368 个候选的真实专业评审、正式 Claim/Evidence、Evaluation、Release 和固定 Release Query 记录。

GridCrew 按 ADR-0030 延期，不属于 M9 P0。当前运行不得用于宣布 M9/R1 验收通过。
