# ADR-0035：阶段 C 固定 Release 知识回接

Status: Accepted for implementation under explicit Stage C authorization (2026-09-09).

1. 新增 POST `/forecast-artifacts/{id}/knowledge-context`，输入固定 release_id 与有界 question。由 Forecast 授权读取、同空间检查、query.release 授权和既有 Release Query 组合；模型调用仍由既有 Gateway 执行，不新增 Provider/依赖/Workflow/迁移。
2. Query 的 direct_answer/召回正文不直接作为本接口依据。仅取其候选 Citation，再从同一 Release 的 Claim/Evidence 冻结快照恢复 statement；重查当前 ACCEPTED Evidence、VALID Anchor、源未失效/未归档、源密级与发布检索投影密级。未通过的引用及主张均不返回。不读当前可变 Entity/Claim 文本充当旧版本知识。
3. 同一接口返回 ForecastArtifact/checksum、固定 Release/manifest checksum、查询记录 ID、当前检查时间与逐条支持材料。相关性由用户问题检索表达，不能自动认定设备适用性、因果、故障概率或专家批准。默认提问不伪造领域术语；用户可输入故障模式、规程或案例关键词。
4. 返回是读时组合解释，不是新增权威 Knowledge 对象或 ForecastArtifact 修订；原 Forecast 中历史“无 Release”标记保持真实。UI 将历史产物与本次回接分开，分别展示 Observed/Forecast/Hypothesis 与 Released Knowledge，来源链不伪装为 R1 正式关系图。
5. 服务再次校验每次请求的当前访问；不缓存客户端可见证据。复用 Query 的技术审计，再记录 artifact→release→query 与引用数量的组合审计。不把既有旧 Graph/Query 广泛问题在 C 中宣称全面解决。
6. UI 的 artifact、Release 或问题改变时清空已显示依据，忽略已过期异步响应。无证据时明确说明不足，不能借 Forecast 补全证据。

技术验证使用显式合成材料/测试角色；保留 M9 专家/阈值和工业效果验收边界，停止在 C，不进入 M10。
