# ADR-0007: 数据库为业务权威，Markdown/YAML 为可交换知识表示

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构/产品负责人
- Related: OQ-MARKDOWN-001, SPK-003

## Context

Wiki 需要 Markdown 编辑、Obsidian 和 Git 导出，但 Entity、Claim、Evidence、审核、权限和 Release 具有结构化事务语义。以文件为唯一权威会导致并发、授权和引用失配；以 DB 隐藏交换语义又会损害可移植性。

## Decision question

数据库、Markdown/YAML 和 Git 各承担什么权威角色？

## Options

1. Git/Markdown 唯一权威；2. 数据库唯一不可导出状态；3. 数据库保存业务权威，Markdown/YAML 是版本化交换/展示表示。

## Decision

选择 3。WikiPageVersion 保存 canonical 结构与内容；导出含稳定 ID、版本和 checksum；回导进入 Draft/diff/conflict，不覆盖 Release。

## Consequences

正面：结构治理、权限、事务和开放交换兼得。负面：需要 round-trip、diff、人工保护区和冲突映射。

## Migration risks

双向同步若无 canonical schema 会形成双权威；Git commit 不自动等于 Release 或 Approval。

## Validation

SPK-003 对属性、正文、链接、Evidence、人工保护区、并发和回导做无语义丢失测试。
