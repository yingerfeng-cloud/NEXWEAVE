# ADR-0003: Python/FastAPI 作为产品核心后端

- Status: Accepted
- Approval basis: M0 任务书 + 用户于 2026-08-23 明确下发 M0
- Date: 2026-08-23
- Decision owners: 架构负责人、研发/运维负责人
- Related: OQ-TECH-001, SPK-009, ADR-0012

## Context

文档解析、模型编排和 Temporal Python SDK 与 Python 生态契合；PRD 又提出 Java/Spring Boot 或企业标准栈。双内核会复制领域、权限和 Release 语义。

## Decision question

产品核心使用 Python/FastAPI、Java/Spring Boot，还是双核心？

## Options

1. Python/FastAPI 单一产品核心；2. Java 核心 + Python AI 服务；3. 双套业务核心。

## Decision

选择 1：Python 3.12、FastAPI、Pydantic、SQLAlchemy、Alembic；企业 Java 需求通过 API/网关/适配壳处理。SPK-009 继续验证交付适配风险，但不再阻塞 M0 产品核心骨架。

## Consequences

正面：减少跨语言领域复制，LLM/解析/Workflow 工具链一致。负面：企业 Java 团队接受度、CPU 密集解析、类型/依赖治理和运维能力需验证。

## Migration risks

如果先编码后决定，ORM、异步、契约生成和部署会大规模返工。系统 Python 3.9 不满足候选基线，需可复现 Python 3.12 环境。

## Validation

SPK-009 验证契约、OTel、并发、依赖/镜像治理、Temporal、Java 壳互操作和团队运维要求。
