import { useCallback, useEffect, useState, type FormEvent } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  GovernanceStepper,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import { ReviewEvidenceView } from "./ReviewEvidenceView";
import { targetText } from "./reviewText";
import type {
  ConflictCase,
  ReviewCase,
  ReviewPolicy,
  ReviewTarget,
} from "./types";

type Props = { api: NexweaveApi; spaceId: string };
const STAGES: Record<string, string> = {
  ENGINEERING: "工程审核（knowledge_engineer）",
  EXPERT: "专家审核（reviewer）",
  APPROVAL: "独立批准（publisher）",
};

export function ReviewCenter(props: Props) {
  return <ReviewView key={props.spaceId} {...props} />;
}

function ReviewView({ api, spaceId }: Props) {
  const [cases, setCases] = useState<ReviewCase[]>([]);
  const [targets, setTargets] = useState<ReviewTarget[]>([]);
  const [policies, setPolicies] = useState<ReviewPolicy[]>([]);
  const [targetId, setTargetId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [reason, setReason] = useState("");
  const [statement, setStatement] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [assignee, setAssignee] = useState("");
  const [risk, setRisk] = useState<ReviewPolicy["risk_level"]>("HIGH");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!spaceId) return;
    try {
      const [c, t, p] = await Promise.all([
        api.reviewCases(spaceId),
        api.reviewTargets(spaceId),
        api.reviewPolicies(spaceId),
      ]);
      setCases(c.items);
      setTargets(t.items);
      setPolicies(p);
      if (t.truncated)
        setNotice("候选超过 500 项，本页显示最新候选；请分批审核后刷新。");
      setError("");
    } catch (cause) {
      setError(messageOf(cause));
    }
  }, [api, spaceId]);
  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(timer);
  }, [load]);
  const target = targets.find((t) => t.id === targetId);
  const policy = policies.find((p) => p.id === policyId);
  const selected = cases.find((c) => c.id === selectedId);
  const actorLabel = (id?: string | null) =>
    id ? (selected?.actor_labels?.[id] ?? id) : "尚无";
  async function createPolicy(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const p = await api.createReviewPolicy(spaceId, {
        risk_level: risk,
        stages:
          risk === "LOW"
            ? ["ENGINEERING"]
            : ["ENGINEERING", "EXPERT", "APPROVAL"],
        timeout_seconds: 3600,
      });
      setPolicyId(p.id);
      await load();
      setNotice("审核策略已保存；请核对后为所选候选起案。");
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function start(event: FormEvent) {
    event.preventDefault();
    if (busy || !target || !policy || !reason.trim()) return;
    setBusy(true);
    try {
      const c = await api.createReviewCase(spaceId, {
        target_type: target.target_type,
        target_id: target.id,
        policy_id: policy.id,
        risk_level: policy.risk_level,
        reason: reason.trim(),
      });
      setSelectedId(c.id);
      setTargetId("");
      setReason("");
      await load();
      setNotice("已绑定服务端版本并起案。请由各阶段业务角色核对证据后操作。");
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function act(decision: string) {
    const task = selected?.tasks.find(
      (t) => t.stage === selected.current_stage,
    );
    if (busy || !selected || !task || !decisionReason.trim()) return;
    setBusy(true);
    try {
      await api.reviewAction(selected, task, {
        decision,
        reason: decisionReason.trim(),
        ...(decision === "MODIFY" ? { change_set: { statement } } : {}),
        ...(decision === "TRANSFER" ? { assignee_id: assignee } : {}),
      });
      setDecisionReason("");
      await load();
      setNotice(
        "审核动作已记录。修改内容会重走审核，最终批准仍执行服务端职责分离。",
      );
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function restart() {
    if (busy || !selected || !decisionReason.trim()) return;
    setBusy(true);
    try {
      await api.restartReview(selected.id, decisionReason.trim());
      setDecisionReason("");
      await load();
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="审核中心"
        description="选择权威候选版本，核对支持与反对证据，逐阶段记录实质判断。"
      />
      <GovernanceStepper current="reviews" />
      {error && <ErrorState message={error} onRetry={load} />}
      {notice && <p role="status">{notice}</p>}
      {!spaceId ? (
        <EmptyState
          title="先选择知识空间"
          description="审核只在当前空间内进行。"
        />
      ) : (
        <>
          <details className="data-card">
            <summary>配置审核策略（空间治理负责人）</summary>
            <form className="m7-form" onSubmit={(e) => void createPolicy(e)}>
              <label>
                风险等级
                <select
                  value={risk}
                  onChange={(e) => setRisk(e.target.value as typeof risk)}
                >
                  <option value="HIGH">高风险 · 三阶段独立终审</option>
                  <option value="MEDIUM">中风险 · 三阶段</option>
                  <option value="LOW">低风险 · 工程审核</option>
                </select>
              </label>
              <p>
                高风险最终批准人不能是原作者、实质编辑者或前序审核者。策略超时为每阶段
                1 小时。
              </p>
              <button type="submit" disabled={busy}>
                保存审核策略
              </button>
            </form>
          </details>
          <form className="data-card m7-form" onSubmit={(e) => void start(e)}>
            <h2>提交审核</h2>
            <label>
              候选内容
              <select
                required
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
              >
                <option value="">请明确选择候选</option>
                {targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {targetText(t)}
                    {t.open_review_case_id ? "（已有审核）" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              审核策略
              <select
                required
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
              >
                <option value="">请选择策略与版本</option>
                {policies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.risk_level} · v{p.version} ·{" "}
                    {p.stages.map((s) => STAGES[s] ?? s).join(" → ")}
                  </option>
                ))}
              </select>
            </label>
            {target && (
              <ReviewEvidenceView key={target.id} api={api} target={target} />
            )}
            <label>
              起案理由
              <textarea
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <button
              className="primary"
              disabled={
                busy ||
                !target ||
                !policy ||
                !reason.trim() ||
                Boolean(target.open_review_case_id)
              }
            >
              绑定当前版本并提交审核
            </button>
          </form>
          <div className="split-layout">
            <section className="data-card">
              <h2>审核队列</h2>
              {cases.map((c) => (
                <button
                  type="button"
                  className="list-row"
                  key={c.id}
                  onClick={() => {
                    setSelectedId(c.id);
                    setDecisionReason("");
                    setStatement(
                      String(c.target_context?.content.statement ?? ""),
                    );
                  }}
                >
                  <strong>
                    {c.target_context
                      ? targetText(c.target_context)
                      : c.target_type}
                  </strong>
                  <StatusPill value={c.status} />
                  <small>
                    {STAGES[c.current_stage ?? ""] ?? "已完成"} · 投递{" "}
                    {c.workflow_delivery_status ?? "待核查"}
                  </small>
                </button>
              ))}
              {!cases.length && <p>还没有审核个案，请先选择编译候选并提交。</p>}
            </section>
            <section className="data-card">
              <h2>版本、证据与阶段操作</h2>
              {selected ? (
                <>
                  <p>
                    起案人：{actorLabel(selected.created_by)} · 起案理由：
                    {selected.reason}
                  </p>
                  {selected.target_context && (
                    <ReviewEvidenceView
                      key={selected.id}
                      api={api}
                      target={selected.target_context}
                    />
                  )}
                  <h3>被审版本与差异</h3>
                  {selected.content_revisions?.map((r, index, all) => (
                    <article key={r.revision} className="list-row">
                      <strong>
                        版本 {r.revision} · 原作者{" "}
                        {actorLabel(r.original_author_id)}
                      </strong>
                      <small>
                        {r.edited_by
                          ? `实质编辑者 ${actorLabel(r.edited_by)}`
                          : "初始绑定 / 重新绑定"}
                      </small>
                      <p>
                        {String(
                          r.content_snapshot.statement ??
                            r.content_snapshot.markdown ??
                            r.content_snapshot.relation_type_key ??
                            "语义提案",
                        )}
                      </p>
                      {index > 0 && (
                        <p>
                          上一版：
                          {String(
                            all[index - 1].content_snapshot.statement ??
                              all[index - 1].content_snapshot.markdown ??
                              all[index - 1].content_snapshot
                                .relation_type_key ??
                              "语义提案",
                          )}
                        </p>
                      )}
                      <TechnicalDetails>
                        <code>{r.content_checksum}</code>
                        <pre>{JSON.stringify(r.content_snapshot, null, 2)}</pre>
                      </TechnicalDetails>
                    </article>
                  ))}
                  {selected.tasks.map((t) => (
                    <p key={t.id}>
                      {STAGES[t.stage] ?? t.stage}：
                      <StatusPill value={t.status} />· 审核者{" "}
                      {actorLabel(t.claimed_by ?? t.assignee_id)}
                    </p>
                  ))}
                  {selected.status === "APPROVED" && (
                    <p>最终批准人：{actorLabel(selected.updated_by)}</p>
                  )}
                  {selected.current_stage && (
                    <>
                      <label>
                        本阶段的实质理由
                        <textarea
                          required
                          value={decisionReason}
                          onChange={(e) => setDecisionReason(e.target.value)}
                        />
                      </label>
                      {selected.target_type === "CLAIM_CANDIDATE" && (
                        <label>
                          修改后的主张正文
                          <textarea
                            value={statement}
                            onChange={(e) => setStatement(e.target.value)}
                          />
                        </label>
                      )}
                      <div className="toolbar">
                        {[
                          ["ACCEPT", "接受并推进"],
                          ["REJECT", "驳回"],
                          ["REQUEST_EVIDENCE", "请求补充证据"],
                        ].map(([d, label]) => (
                          <button
                            type="button"
                            key={d}
                            disabled={busy || !decisionReason.trim()}
                            onClick={() => void act(d)}
                          >
                            {label}
                          </button>
                        ))}
                        {selected.target_type === "CLAIM_CANDIDATE" && (
                          <button
                            type="button"
                            disabled={
                              busy ||
                              !decisionReason.trim() ||
                              !statement.trim()
                            }
                            onClick={() => void act("MODIFY")}
                          >
                            提交实质修改并重审
                          </button>
                        )}
                        <button
                          type="button"
                          disabled={busy || !decisionReason.trim()}
                          onClick={() => void restart()}
                        >
                          重新绑定当前内容并重审
                        </button>
                      </div>
                      <details>
                        <summary>转交同阶段人员</summary>
                        <label>
                          已获相应角色的用户 ID
                          <input
                            value={assignee}
                            onChange={(e) => setAssignee(e.target.value)}
                          />
                        </label>
                        <button
                          type="button"
                          disabled={busy || !decisionReason.trim() || !assignee}
                          onClick={() => void act("TRANSFER")}
                        >
                          转交
                        </button>
                      </details>
                    </>
                  )}
                  <h3>审核记录</h3>
                  {selected.actions?.map((a) => (
                    <article key={a.id} className="list-row">
                      <strong>
                        {STAGES[a.stage] ?? a.stage} · {a.decision}
                      </strong>
                      <p>{a.reason}</p>
                      <small>
                        {actorLabel(a.created_by)} ·{" "}
                        {new Date(a.created_at).toLocaleString()}
                      </small>
                    </article>
                  ))}
                </>
              ) : (
                <p>选择一个审核个案，核对正文与证据后再操作。</p>
              )}
            </section>
          </div>
        </>
      )}
    </section>
  );
}

export function ConflictCenter(props: Props) {
  return <ConflictView key={props.spaceId} {...props} />;
}

function ConflictView({ api, spaceId }: Props) {
  const [items, setItems] = useState<ConflictCase[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [resolution, setResolution] = useState("RETAIN_BOTH");
  const [reason, setReason] = useState("");
  const [conditions, setConditions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) return;
    try {
      setItems((await api.conflicts(spaceId)).items);
      setError("");
    } catch (cause) {
      setError(messageOf(cause));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  const selected = items.find((c) => c.id === selectedId);
  async function detect() {
    if (busy) return;
    setBusy(true);
    try {
      setItems((await api.detectConflicts(spaceId)).items);
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function decide(event: FormEvent) {
    event.preventDefault();
    if (busy || !selected || !reason.trim()) return;
    setBusy(true);
    try {
      await api.resolveConflict(selected.id, {
        resolution,
        reason: reason.trim(),
        conditions:
          resolution === "CONDITIONAL"
            ? { applicability: conditions.trim() }
            : {},
      });
      setReason("");
      await load();
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="冲突中心"
        description="并排核对双方内容与原文；由空间治理负责人以有理由的裁决更新阻断，保留全部历史。"
      />
      <GovernanceStepper current="conflicts" />
      {error && <ErrorState message={error} onRetry={load} />}
      <button
        type="button"
        disabled={busy || !spaceId}
        onClick={() => void detect()}
      >
        从编译结果检测冲突
      </button>
      <div className="split-layout">
        <section className="data-card">
          <h2>冲突队列</h2>
          {items.map((c) => (
            <button
              type="button"
              className="list-row"
              key={c.id}
              onClick={() => {
                setSelectedId(c.id);
                setReason("");
                setConditions("");
              }}
            >
              <strong>{c.kind}</strong>
              <StatusPill value={c.status} />
              <small>
                {c.blocking && ["OPEN", "UNRESOLVED"].includes(c.status)
                  ? "当前阻断发布"
                  : "当前不阻断发布"}
              </small>
            </button>
          ))}
          {!items.length && <p>当前没有可见冲突。</p>}
        </section>
        <section className="data-card">
          <h2>双方依据与裁决</h2>
          {selected ? (
            <>
              {selected.items?.map((t) => (
                <article key={`${t.side}:${t.id}`}>
                  <h3>{t.side} 方</h3>
                  <ReviewEvidenceView api={api} target={t} />
                </article>
              ))}
              <form className="m7-form" onSubmit={(e) => void decide(e)}>
                <label>
                  裁决方式
                  <select
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                  >
                    <option value="RETAIN_BOTH">
                      保留双方（记录适用范围）
                    </option>
                    <option value="CONDITIONAL">按明确条件成立</option>
                    <option value="EXPIRED">依据过期，结束此冲突</option>
                    <option value="UNRESOLVED">
                      仍未解决（阻断以冲突等级为准）
                    </option>
                    <option value="REOPEN">重新打开（恢复适用阻断）</option>
                  </select>
                </label>
                <label>
                  裁决理由
                  <textarea
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                {resolution === "CONDITIONAL" && (
                  <label>
                    成立条件
                    <textarea
                      required
                      value={conditions}
                      onChange={(e) => setConditions(e.target.value)}
                    />
                  </label>
                )}
                <button
                  className="primary"
                  disabled={
                    busy ||
                    !reason.trim() ||
                    (resolution === "CONDITIONAL" && !conditions.trim())
                  }
                >
                  记录裁决并更新阻断
                </button>
              </form>
              <h3>裁决历史</h3>
              {selected.decisions?.map((d, i) => (
                <article className="list-row" key={i}>
                  <strong>{d.resolution}</strong>
                  <p>{d.reason}</p>
                  {Object.keys(d.conditions).length > 0 && (
                    <pre>{JSON.stringify(d.conditions, null, 2)}</pre>
                  )}
                  <small>
                    {new Date(d.created_at).toLocaleString()} · {d.created_by}
                  </small>
                </article>
              ))}
            </>
          ) : (
            <p>选择冲突，查看双方证据后裁决。</p>
          )}
        </section>
      </div>
    </section>
  );
}
