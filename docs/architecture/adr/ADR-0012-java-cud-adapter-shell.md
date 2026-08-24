# ADR-0012: 企业 Java/CUD4.0 适配壳而非第二套知识内核

- Status: Accepted
- Approval basis: M0 单一产品核心决策；正式国产化认证仍属 M12
- Date: 2026-08-23
- Decision owners: 架构/交付负责人
- Related: OQ-DAMENG-001, SPK-009, ADR-0003

## Context

部分客户要求 Java、CUD4.0、达梦或国产中间件。为每类环境复制知识编译、证据、审核和 Release 内核会造成长期语义分裂。

## Decision question

企业适配应修改/复制产品核心，还是通过标准 API、Provider、网关和部署壳实现？

## Options

1. 客户专用内核分支；2. Java 重写产品核心；3. 单一产品内核 + Java/API 网关/数据库 Provider/部署适配壳。

## Decision

选择 3。客户壳负责协议、IAM、网关、部署和合规适配，不拥有 Knowledge/Release 业务权威。数据库方言差异通过 Adapter 和契约测试处理。

## Consequences

正面：单一语义内核、升级可控、客户逻辑隔离。负面：适配层和兼容认证仍有成本，某些环境可能要求部署例外。

## Migration risks

若核心 SQL、身份或对象存储语义绑定 PostgreSQL/云服务，适配会失败；若 Java 壳保存业务状态，会形成第二套权威。

## Validation

SPK-009 验证 Java 壳互操作、OIDC/API、错误/幂等/审计、部署约束；M12 执行国产化正式认证。
