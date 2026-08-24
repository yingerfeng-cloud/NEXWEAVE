# ADR-0011: GridCrew Knowledge Pack → Skill 映射

- Status: Accepted
- Approval basis: 独立产品边界与固定 Release 原则；具体租户映射仍在 M8 前联合冻结
- Date: 2026-08-23
- Decision owners: 双方产品/架构负责人
- Related: SPK-008, OQ-GRID-001

## Context

GridCrew Skill/EmployeeRelease 是版本化执行资产；NEXWEAVE DomainPack/Release 是版本化知识资产。简单按“当前版本”查询会让运行中任务不可复现。

## Decision question

GridCrew 如何引用 NEXWEAVE 知识能力和版本？

## Options

1. Skill 复制知识；2. Skill 指向空间当前版本；3. Skill Version 保存 provider、tenant mapping、space、release、Pack、query policy 和允许操作。

## Decision

选择 3。GridCrew EmployeeRelease/Task 锁定 Skill Version，进而锁定 NEXWEAVE Release。发布事件只提示升级，不自动改变运行中任务。

## Consequences

正面：版本可复现、权限最小、两产品独立。负面：映射、废止、权限变更、双审计和缓存失效更复杂。

## Migration risks

Pack 版本与 Release 不是一一对应；NEXWEAVE Evidence 与 GridCrew Evidence 不合并；反馈只能进入草稿。

## Validation

SPK-008 联合契约 fixture 验证固定版本、越权、Evidence、Graph、超时重试、废止事件和反馈回执。
