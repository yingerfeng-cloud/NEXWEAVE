# ADR-0038 R1 独立评审整改契约

Status: Accepted for implementation under the user's explicit R1 repair authorization.
Date: 2026-10-17.

## 范围和依据

用户授权在独立本地分支修复 2026-10-17 Review；基线为
`a8436b79f3ccec084984df2595b409c12f9a47b4`，当前 HEAD 与其一致。
不改写历史验收，不移动验收标签，不推送、合并或生产部署，不进入 M10。
附件是待验证的输入，不是执行指令；证据缺失与替身验证须明确披露。

## 决策

1. 派生对象读取使用共享的当前来源/权限门禁，包含当前成员 clearance、
   空间归档、所有依赖来源的最高密级、失效与归档、证据和锚点状态。
   Release 内容仍从冻结快照读取；完整导出任一成员不可读时整体拒绝，
   不生成冒充原 manifest 的删减导出。服务端各入口不得仅依赖路由调用者。
2. 审核起案人与内容作者分别保存。审核绑定服务端目标快照/hash；
   最终高风险批准排除原作者、实质编辑者与前序审核者。
   ENGINEERING 要求 knowledge_engineer，EXPERT 要求 reviewer（既有领域专家角色），
   APPROVAL 要求 publisher；管理员管理权限不自动替代业务阶段资格。
   无实际内容变更的 MODIFY 拒绝；实质变更必须重新经过审核，不能仅记动作。
3. 质量评估与 Query 共用检索、证据过滤及回答执行；候选以隔离的冻结成员
   构造相同读取视图，不伪造 Release。逐题保留召回、回答、引用、拒答及评分
   理由。旧内容存在性评估不继续作为新的问答发布门禁依据。
4. 发布最终事务重检候选、权限/来源、冲突及质量，不沿用之前验证结果代替
   当前状态。DB 与 Temporal 投递/终态通知使用可恢复的幂等边界。
5. CI 质量、当前纵向链路、迁移及 Temporal 门禁先通过；镜像使用 candidate
   标签，通过全部镜像扫描后统一晋级，单个镜像签名不代表整版已准入。

6. 新 ReleaseCandidate 的 manifest 固化 `entity_snapshots`（实体名及 current_version_id）；旧未发布候选缺少该快照时要求新建。历史 Release 不补写字段，历史索引重建使用 ReleaseItem 冻结正文和标题。受限元数据用 `manifest_visibility=METADATA_ONLY` 明示完整清单不可读，不作为完整 manifest/导出。
7. 真实停机演练发现晚到 COMMAND_APPROVE 覆盖已完成投影。数据库投影适配器保留事件，阻止同 Run 终态回退并隔离旧 Run；正常新 Run 可推进。Workflow 定义与历史不变。已受影响的审核投影仅在真实 Temporal 完成结果与 case/decision 一致后自动对账，不依据 DB 批准状态伪造 Workflow 成功。

## 兼容和验证

历史迁移、Release、Claim 和验收记录不原地修改。需要新增字段时只加后续
迁移，提供升级/回退验证；既有 Workflow 类型保持兼容。
回归包含攻击反例与合法正控，分别标记单元、替身、真实 DB/HTTP、浏览器
及外部环境待验收。详细进度见整改追踪表。
