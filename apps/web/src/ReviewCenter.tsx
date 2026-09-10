import { useCallback, useEffect, useState } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  GovernanceStepper,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type { Claim, ConflictCase, ReviewCase } from "./types";

export function ClaimCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selected, setSelected] = useState<Claim | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setClaims([]);
      setSelected(null);
      setError("");
      return;
    }
    try {
      setClaims((await api.claims(spaceId)).items);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取正式主张。"));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  return (
    <section className="content-page">
      <PageHeader
        title="主张与证据"
        description="主张是可被审核和引用的知识陈述；每条正式主张都必须保留来源与证据链。"
      />
      <GovernanceStepper current="claims" />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="主张与证据只展示当前知识空间的正式内容。"
        />
      )}
      <div className="split-layout claim-layout">
        <div className="data-card">
          <h2>已批准主张</h2>
          {claims.map((claim) => (
            <button
              className="list-row"
              key={claim.id}
              type="button"
              onClick={() => setSelected(claim)}
            >
              <strong>{claim.statement}</strong>
              <StatusPill value={claim.status} />
            </button>
          ))}
          {!claims.length && (
            <EmptyState
              title="还没有已批准的主张"
              description="完成候选知识的人工审核后，正式主张及其证据会出现在这里。"
            />
          )}
        </div>
        <div className="data-card claim-detail">
          <h2>主张详情</h2>
          {selected ? (
            <>
              <blockquote>{selected.statement}</blockquote>
              <dl className="detail-list">
                <div>
                  <dt>可信度</dt>
                  <dd>{selected.confidence_level}</dd>
                </div>
                <div>
                  <dt>知识关系</dt>
                  <dd>{selected.predicate_key}</dd>
                </div>
                <div>
                  <dt>状态</dt>
                  <dd>
                    <StatusPill value={selected.status} />
                  </dd>
                </div>
              </dl>
              <TechnicalDetails>
                <pre>{JSON.stringify(selected.provenance, null, 2)}</pre>
              </TechnicalDetails>
            </>
          ) : (
            <EmptyState
              title="选择一条主张"
              description="在左侧选择主张，查看内容、可信度和来源信息。"
            />
          )}
        </div>
      </div>
    </section>
  );
}

export function ConflictCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [conflicts, setConflicts] = useState<ConflictCase[]>([]);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setConflicts([]);
      setError("");
      return;
    }
    try {
      setConflicts((await api.conflicts(spaceId)).items);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取冲突。"));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  async function unresolved(conflict: ConflictCase) {
    if (workingId) return;
    setWorkingId(conflict.id);
    try {
      await api.resolveConflict(conflict.id, {
        resolution: "UNRESOLVED",
        reason: "需要保留双方证据并等待专家裁决",
      });
      await load();
    } catch (cause) {
      setError(messageOf(cause, "冲突处置失败。"));
    } finally {
      setWorkingId("");
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="冲突中心"
        description="冲突会保留双方对象、证据快照与裁决理由；阻断项必须在发布前处置。"
      />
      <GovernanceStepper current="conflicts" />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="冲突队列需要读取当前知识空间的主张与证据关系。"
        />
      )}
      <div className="data-card">
        <h2>冲突队列</h2>
        {conflicts.map((conflict) => (
          <article className="list-row" key={conflict.id}>
            <strong>
              {conflictKindLabel(conflict.kind)} · {conflict.cluster_key}
            </strong>
            <small>
              {severityLabel(conflict.severity)} ·{" "}
              {conflict.blocking ? "阻断" : "非阻断"} ·{" "}
              <StatusPill value={conflict.status} />
            </small>
            {conflict.status === "OPEN" && (
              <button
                type="button"
                disabled={Boolean(workingId)}
                onClick={() => void unresolved(conflict)}
              >
                {workingId === conflict.id ? "处理中…" : "标记未决"}
              </button>
            )}
          </article>
        ))}
        {!conflicts.length && (
          <EmptyState
            title="当前没有待处理冲突"
            description="知识编译识别到相互矛盾的主张后，会在这里创建冲突个案。"
          />
        )}
      </div>
    </section>
  );
}

export function ReviewCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [cases, setCases] = useState<ReviewCase[]>([]);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setCases([]);
      setError("");
      return;
    }
    try {
      setCases((await api.reviewCases(spaceId)).items);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取审核队列。"));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  async function act(reviewCase: ReviewCase, decision: "ACCEPT" | "REJECT") {
    if (workingId) return;
    const task = reviewCase.tasks.find(
      (item) => item.stage === reviewCase.current_stage,
    );
    if (!task) return;
    setWorkingId(reviewCase.id);
    try {
      await api.reviewAction(reviewCase, task, {
        decision,
        reason: `审核中心 ${decision === "ACCEPT" ? "接受" : "驳回"}`,
      });
      await load();
    } catch (cause) {
      setError(messageOf(cause, "审核动作失败。"));
    } finally {
      setWorkingId("");
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="审核中心"
        description="按风险等级组织人工审核，高风险终审保持职责分离并完整记录裁决。"
      />
      <GovernanceStepper current="reviews" />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="审核队列需要读取当前知识空间的治理任务。"
        />
      )}
      <div className="data-card">
        <h2>审核队列</h2>
        {cases.map((reviewCase) => (
          <article className="list-row" key={reviewCase.id}>
            <strong>
              {targetLabel(reviewCase.target_type)} ·{" "}
              {riskLabel(reviewCase.risk_level)}
            </strong>
            <small>
              <StatusPill value={reviewCase.status} /> · 当前阶段{" "}
              {reviewCase.current_stage || "已完成"}
            </small>
            <small>
              {reviewCase.tasks
                .map(
                  (task) =>
                    `${stageLabel(task.stage)}：${statusLabel(task.status)}`,
                )
                .join(" · ")}
            </small>
            {reviewCase.status === "OPEN" && (
              <div>
                <button
                  type="button"
                  disabled={Boolean(workingId)}
                  onClick={() => void act(reviewCase, "ACCEPT")}
                >
                  {workingId === reviewCase.id ? "处理中…" : "接受"}
                </button>
                <button
                  type="button"
                  disabled={Boolean(workingId)}
                  onClick={() => void act(reviewCase, "REJECT")}
                >
                  {workingId === reviewCase.id ? "处理中…" : "驳回"}
                </button>
              </div>
            )}
          </article>
        ))}
        {!cases.length && (
          <EmptyState
            title="当前没有待审核任务"
            description="编译产生新的候选主张或关系后，符合策略的内容会进入这里等待审核。"
          />
        )}
      </div>
    </section>
  );
}

function statusLabel(value: string) {
  return (
    {
      PENDING: "待处理",
      ACCEPTED: "已通过",
      REJECTED: "已拒绝",
      COMPLETED: "已完成",
      OPEN: "待处理",
      APPROVED: "已批准",
    }[value] ?? value
  );
}

function targetLabel(value: string) {
  return (
    {
      CLAIM_CANDIDATE: "候选主张",
      RELATION_CANDIDATE: "候选关系",
      WIKI_PAGE: "Wiki 页面",
    }[value] ?? value
  );
}

function riskLabel(value: string) {
  return (
    {
      LOW: "低风险",
      MEDIUM: "中风险",
      HIGH: "高风险",
      CRITICAL: "极高风险",
    }[value] ?? value
  );
}

function stageLabel(value: string) {
  return (
    {
      ENGINEERING: "工程审核",
      EXPERT: "专家审核",
      APPROVAL: "发布审批",
    }[value] ?? value
  );
}

function conflictKindLabel(value: string) {
  return (
    {
      DUPLICATE_CLAIM: "重复主张",
      CONTRADICTORY_CLAIM: "矛盾主张",
      RELATION_CONFLICT: "关系冲突",
    }[value] ?? value
  );
}

function severityLabel(value: string) {
  return (
    {
      LOW: "低严重度",
      MEDIUM: "中严重度",
      HIGH: "高严重度",
      CRITICAL: "极高严重度",
    }[value] ?? value
  );
}
