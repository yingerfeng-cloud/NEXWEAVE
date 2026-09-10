import { useCallback, useEffect, useState } from "react";

import { messageOf, type NexweaveApi } from "./api";
import {
  DataTable,
  ErrorState,
  EmptyState,
  Metric,
  PageHeader,
  Panel,
  StatusPill,
} from "./design-system/ui";
import type { AuditLog, Principal, Role, Space } from "./types";

export function OverviewPage({
  api,
  principal,
  spaces,
  spaceId,
  onNavigate,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaces: Space[];
  spaceId: string;
  onNavigate?: (route: string) => void;
}) {
  const [audits, setAudits] = useState<AuditLog[]>([]);
  const [auditError, setAuditError] = useState("");
  const [knowledgeError, setKnowledgeError] = useState("");
  const [knowledge, setKnowledge] = useState({
    sources: 0,
    schemas: 0,
    claims: 0,
    reviews: 0,
    conflicts: 0,
    release: "—",
    quality: "待配置",
  });
  const canAudit = hasAnyRole(
    principal,
    "platform_admin",
    "tenant_admin",
    "auditor",
  );
  const loadAudits = useCallback(async () => {
    if (!canAudit) return;
    setAuditError("");
    try {
      setAudits((await api.audits()).items);
    } catch (error) {
      setAuditError(messageOf(error, "无法读取最近活动。"));
    }
  }, [api, canAudit]);

  useEffect(() => void loadAudits(), [loadAudits]);
  const loadKnowledge = useCallback(async () => {
    if (!spaceId) return;
    setKnowledgeError("");
    const [sources, schemas, claims, reviews, conflicts, releases, suites] =
      await Promise.all([
        api.sources(spaceId, { limit: 100 }),
        api.schemas(spaceId),
        api.claims(spaceId),
        api.reviewCases(spaceId),
        api.conflicts(spaceId),
        api.releases(spaceId),
        api.evaluationSuites(spaceId),
      ]);
    setKnowledge({
      sources: sources.items.length,
      schemas: schemas.items.length,
      claims: claims.items.length,
      reviews: reviews.items.filter((item) => item.status === "OPEN").length,
      conflicts: conflicts.items.filter((item) => item.status === "OPEN")
        .length,
      release: releases.items[0]?.version ?? "—",
      quality: statusLabel(suites[0]?.status),
    });
  }, [api, spaceId]);

  useEffect(() => {
    void loadKnowledge().catch((error) => setKnowledgeError(messageOf(error)));
  }, [loadKnowledge]);
  return (
    <section className="page">
      <PageHeader
        title="平台总览"
        description="从资料进入知识模型，经证据治理与人工审核，最终形成可追溯的不可变发布。"
        actions={
          <>
            <a
              className="btn"
              href="/reviews"
              onClick={(event) => {
                if (!onNavigate) return;
                event.preventDefault();
                onNavigate("reviews");
              }}
            >
              查看待审核
            </a>
            <a
              className="btn primary"
              href="/sources"
              onClick={(event) => {
                if (!onNavigate) return;
                event.preventDefault();
                onNavigate("sources");
              }}
            >
              进入资料中心 →
            </a>
          </>
        }
      />
      <div className="metric-grid overview-metrics">
        <Metric
          value={knowledge.sources + knowledge.claims}
          label="知识资产"
          detail={`${knowledge.sources} 份资料 · ${knowledge.claims} 条主张`}
        />
        <Metric
          value={knowledge.reviews}
          label="待审核"
          detail="需要人工判断"
        />
        <Metric
          value={knowledge.conflicts}
          label="待解决冲突"
          detail="发布前必须处置"
        />
        <Metric
          value={knowledge.release}
          label="当前发布"
          detail="不可变知识版本"
        />
        <Metric
          value={knowledge.quality}
          label="质量状态"
          detail="发布前门禁"
        />
      </div>
      {!spaceId && (
        <EmptyState
          title="先选择或创建知识空间"
          description="总览指标会随当前知识空间更新；前往空间管理创建第一个工作区。"
          primaryAction={
            <a className="btn primary" href="/spaces">
              管理知识空间
            </a>
          }
        />
      )}
      {knowledgeError && (
        <ErrorState message={knowledgeError} onRetry={loadKnowledge} />
      )}
      <Panel title="可信知识生命周期">
        <div className="lifecycle-flow">
          {[
            ["资料", knowledge.sources, "汇集可信来源", "/sources"],
            ["建模", knowledge.schemas, "定义知识结构", "/schemas"],
            ["主张", knowledge.claims, "绑定证据依据", "/claims"],
            ["审核", knowledge.reviews, "完成专家判断", "/reviews"],
            ["发布", knowledge.release, "形成稳定版本", "/releases"],
          ].map(([label, value, detail, href]) => (
            <a
              key={label}
              href={String(href)}
              aria-label={`进入${label}`}
              onClick={(event) => {
                if (!onNavigate) return;
                event.preventDefault();
                onNavigate(String(href).replace(/^\//, ""));
              }}
            >
              <span>{label}</span>
              <strong title={String(value)}>{value}</strong>
              <small>{detail}</small>
            </a>
          ))}
        </div>
      </Panel>
      <div className="two-column overview-secondary">
        <Panel title="空间概况">
          <DataTable
            headers={["空间", "状态", "版本"]}
            rows={spaces.map((space) => [
              space.display_name,
              <StatusPill value={space.status} />,
              `v${space.version}`,
            ])}
            empty="尚未创建知识空间"
          />
        </Panel>
        <Panel title="最近活动与风险">
          {auditError ? (
            <ErrorState message={auditError} onRetry={loadAudits} />
          ) : (
            <DataTable
              headers={["动作", "结果", "时间"]}
              rows={audits
                .slice(0, 5)
                .map((item) => [
                  auditActionLabel(item.action),
                  auditOutcomeLabel(item.outcome),
                  formatDate(item.occurred_at),
                ])}
              empty={canAudit ? "近期没有活动" : "当前账号不可查看审计活动"}
            />
          )}
        </Panel>
      </div>
    </section>
  );
}

function hasAnyRole(principal: Principal, ...roles: Role[]) {
  return roles.some((role) => principal.roles.includes(role));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function auditActionLabel(value: string) {
  const [resource, action] = value.split(".");
  const resourceLabel = {
    governance: "治理配置",
    release: "发布",
    schema: "知识模型",
    claim: "主张",
    source: "资料",
    space: "知识空间",
  }[resource];
  const actionLabel = {
    read: "查看",
    manage: "管理",
    create: "创建",
    update: "更新",
    publish: "发布",
  }[action];
  return resourceLabel && actionLabel
    ? `${actionLabel}${resourceLabel}`
    : "平台操作";
}

function auditOutcomeLabel(value: string) {
  return (
    {
      ALLOWED: "已允许",
      DENIED: "已拒绝",
      SUCCEEDED: "已完成",
      FAILED: "失败",
    }[value] ?? value
  );
}

function statusLabel(value?: string) {
  if (!value) return "待配置";
  return (
    {
      ACTIVE: "启用",
      AVAILABLE: "可用",
      PUBLISHED: "已发布",
      PASSED: "已通过",
      FAILED: "失败",
      PARTIAL_FAILED: "部分失败",
      TESTING: "验证中",
    }[value] ?? value.replaceAll("_", " ")
  );
}
