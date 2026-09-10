# M9 公开 Equipment RCA 候选资料目录

> 批次：`M9-PUBLIC-RCA-CANDIDATE-2026-09-01`  
> 获取日期：2026-09-01  
> 状态：9 份资料已完成本地仅文本准入；其中 4 份已完成 Raw 保留、文本派生 Source 与候选编译，但不是专家验收证据

## 使用边界

本批次优先选择 NTSB 官方事故调查报告。NTSB 的[网站政策](https://www.ntsb.gov/about/Pages/Website-Policies.aspx)说明，除另有标注外，其工作人员履职形成的网页、报告、建议和公开 docket 内容不受版权保护；但报告中来自第三方的照片、插图、地图、厂商资料和其他标识内容不自动获得再利用授权。

因此首轮仅准备用于正文和表格的文本化、证据定位与知识建模。所有 `Source`、`Courtesy` 或版权标识的第三方图像/附件默认排除；NTSB 徽章和标志不使用。未经另行批准，资料不得发送到外部模型。

## 已取得资料

| ID | 报告 | 页数 | 适合验证的故障链 | 官方来源 |
|---|---:|---:|---|---|
| NTSB-MIR-22-06 | Diesel Generator Engine Failure aboard Ferry *Wenatchee* | 14 | 大修装配、紧固扭矩、润滑丧失、连杆破坏、火灾隔离 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/MIR2206.pdf) |
| NTSB-MAB-21-26 | Diesel Generator Engine Failure aboard *Ocean Intervention* | 11 | 连杆轴承粘连、曲轴与连杆失效、机舱火灾 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/MAB2126.pdf) |
| NTSB-MAB-19-02 | Diesel Generator Failure aboard *Red Dawn* | 7 | 连接螺栓扭矩、组件松脱、过载与二次损伤 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/MAB1902.pdf) |
| NTSB-MAB-18-01 | Grounding of Bulk Carrier *Nenita* | 11 | 冷却夹套、紧固件、冷却水泄漏、降速与失控 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/MAB1801.pdf) |
| NTSB-MAB-17-21 | Engine Room Fire aboard *Carnival Liberty* | 17 | 燃油法兰螺栓、振动、喷油、热表面点燃 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/MAB1721.pdf) |
| NTSB-AAR-18-01 | Uncontained Engine Failure and Fire, Flight 383 | 105 | 涡轮盘制造异常、低周疲劳、检查可探测性与应急程序 | [调查页](https://www.ntsb.gov/investigations/pages/dca17fa021.aspx) |
| NTSB-PIR-22-02 | Danville Natural Gas Pipeline Rupture and Fire | 65 | 硬点、涂层退化、阴极保护、氢致开裂、交互威胁 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/PIR22002.pdf) |
| NTSB-PAR-12-01 | Marshall, Michigan Pipeline Rupture and Oil Spill | 164 | 腐蚀疲劳、涂层剥离、完整性管理、报警误判和重复启动 | [PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/PAR1201.pdf) |
| NTSB-RIR-24-05 | East Palestine Derailment and Hazardous Materials Release | 216 | 轮轴承热失效、路旁检测、阈值与趋势、应急决策 | [更正后 PDF](https://www.ntsb.gov/investigations/AccidentReports/Reports/RIR2405%20CORRECTED.pdf) |

合计：9 份，610 页。完整字节数、SHA-256、许可和准入状态见 `public-source-accession-manifest.json`。

## 补充外部参考（尚未下载/准入）

- FAA [Aviation Maintenance Technician Handbooks](https://www.faa.gov/regulations_policies/handbooks_manuals/aviation)：可补充一般、机体和动力装置原理，但体积较大，且需要按章节核对第三方材料后再决定是否取得。
- FAA [Maintenance Error Decision Aid 与程序遵循资料](https://www.faa.gov/about/initiatives/maintenance_hf/procedural_non-compliance)：适合设计人工失误和程序偏差的评审模板；不作为设备故障事实来源。

这些外部参考只记录链接，不计入 9 份候选语料，也没有试点证据状态。

## 准入结果与后续步骤

1. 逐份文本提取、关键结论页目检和第三方视觉元素排除已完成，详见 `PUBLIC_SOURCE_ADMISSION_REPORT.md`。
2. 首批 4 份代表性案例已创建不可变 Raw 与文本派生 SourceVersion，并完成候选编译和审计；运行证据见 M9 技术试点报告。
3. 下一步由具备签署权限的领域专家批准术语映射、问题集、指标阈值并评审候选；未评审前不创建正式 Release。
4. 其余 5 份已准入报告保留为扩展集；所有结果均标注为“公开资料技术试点”，不得外推为客户现场或特定行业适配结论。
