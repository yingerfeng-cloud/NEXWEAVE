import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type { GraphTraverse, KnowledgeRelease, QueryAnswer } from "./types";

function failure(cause: unknown) {
  return messageOf(cause, "请求未能安全完成。");
}

type AnswerExplanation = {
  title: string;
  detail: string;
  next: string;
};

function explainAnswer(answer: QueryAnswer): AnswerExplanation {
  const reason =
    answer.answer_reason ??
    (answer.status === "COMPLETED"
      ? "SUPPORTED_EVIDENCE"
      : "EVIDENCE_UNAVAILABLE");
  return (
    {
      SUPPORTED_EVIDENCE: {
        title: "已找到可引用依据",
        detail:
          "回答只使用当前固定 Release 中可见、有效且与 Evidence 关联的主张。",
        next: "查看右侧引用，可直接打开经过服务端重新授权的原文定位。",
      },
      NO_MATCHING_KNOWLEDGE: {
        title: "当前发布没有匹配的知识",
        detail:
          "检索没有找到与问题相匹配的已发布知识对象；系统没有把未命中内容当作事实。",
        next: "换用资料中的设备名、部件名或规程术语，并确认当前发布版本。",
      },
      EVIDENCE_UNAVAILABLE: {
        title: "候选内容未通过证据门禁",
        detail:
          "检索到了候选内容，但没有同时满足固定 Release、有效 Anchor、Evidence 和当前权限的可引用依据。",
        next: "到“主张与证据”或“资料”核对来源；系统不会用未引用文本补全回答。",
      },
      HISTORICAL_RECHECK_SUPPORTED: {
        title: "历史回答已重新核验",
        detail:
          "这条历史回答已按当前权限和来源有效性重新投影，保留下来的陈述仍有可见引用。",
        next: "查看右侧引用，确认当前原文位置。",
      },
      HISTORICAL_RECHECK_UNAVAILABLE: {
        title: "历史引用在重新核验后不可用",
        detail:
          "这是历史回答的读时核验结果；原记录未修改，但当前无法保留原来的可见有效引用。",
        next: "回到当前有效资料和发布版本，重新发起查询。",
      },
    }[reason] ?? {
      title: "回答状态需要核查",
      detail:
        "系统没有把未通过固定 Release 和 Evidence 门禁的内容当作正式回答。",
      next: "检查当前发布、资料有效性和访问权限后重试。",
    }
  );
}

export { QualityCenter, ReleaseCenter } from "./QualityReleaseForms";

export function AskCenter({
  api,
  spaceId,
  onNavigate,
}: {
  api: NexweaveApi;
  spaceId: string;
  onNavigate?: (path: string) => void;
}) {
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [releaseId, setReleaseId] = useState("");
  const [question, setQuestion] = useState("");
  const [strategy, setStrategy] = useState("KEYWORD");
  const [predicateFilter, setPredicateFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [answer, setAnswer] = useState<QueryAnswer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const requestEpoch = useRef(0);
  const pending = useRef(false);
  const questionRef = useRef<HTMLTextAreaElement>(null);
  const retryReleases = useCallback(async () => {
    if (!spaceId) return;
    setError("");
    try {
      const result = await api.releases(spaceId);
      setReleases(result.items);
      setReleaseId((current) => current || result.items[0]?.id || "");
    } catch (cause) {
      setError(failure(cause));
    }
  }, [api, spaceId]);
  useEffect(() => {
    let active = true;
    requestEpoch.current += 1;
    pending.current = false;
    setBusy(false);
    setReleases([]);
    setReleaseId("");
    setAnswer(null);
    setQuestion("");
    setError("");
    if (!spaceId) return;
    void api
      .releases(spaceId)
      .then((result) => {
        if (!active) return;
        setReleases(result.items);
        setReleaseId(result.items[0]?.id || "");
      })
      .catch((cause) => {
        if (active) setError(failure(cause));
      });
    return () => {
      active = false;
      requestEpoch.current += 1;
    };
  }, [api, spaceId]);
  async function ask(event: FormEvent) {
    event.preventDefault();
    if (pending.current || !releaseId || !question.trim()) return;
    const epoch = ++requestEpoch.current;
    pending.current = true;
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      const result = await api.askRelease(releaseId, {
        question: question.trim(),
        strategy,
        top_k: 5,
        filters: {
          ...(predicateFilter.trim()
            ? { predicate_key: predicateFilter.trim() }
            : {}),
          ...(subjectFilter.trim()
            ? { subject_entity_id: subjectFilter.trim() }
            : {}),
        },
        client_request_id: crypto.randomUUID(),
      });
      if (epoch === requestEpoch.current) setAnswer(result);
    } catch (cause) {
      if (epoch === requestEpoch.current) setError(failure(cause));
    } finally {
      if (epoch === requestEpoch.current) {
        pending.current = false;
        setBusy(false);
      }
    }
  }
  const explanation = answer ? explainAnswer(answer) : null;
  return (
    <section className="content-page">
      <PageHeader
        title="Ask NEXWEAVE"
        description="向一个确定的不可变发布提问；每个回答都展示证据来源，证据不足时明确拒答。"
      />
      {error && <ErrorState message={error} onRetry={retryReleases} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="Ask NEXWEAVE 只查询当前空间中的不可变发布。"
        />
      )}
      <div className="ask-context-bar">
        <label>
          当前发布
          <select
            value={releaseId}
            onChange={(event) => {
              requestEpoch.current += 1;
              pending.current = false;
              setBusy(false);
              setAnswer(null);
              setError("");
              setReleaseId(event.target.value);
            }}
          >
            {!releases.length && <option value="">暂无可查询发布</option>}
            {releases.map((item) => (
              <option value={item.id} key={item.id}>
                {item.version}
              </option>
            ))}
          </select>
        </label>
        <span>查询范围：当前知识空间 · 已发布知识</span>
      </div>
      <p>
        {strategy === "KEYWORD" || strategy === "ATTRIBUTE"
          ? "当前使用词面/属性检索，返回经审核的原文摘录；未调用语义模型。"
          : "当前策略需要真实 embedding 模型及该发布的对应投影；模型不可用时会明确报错。"}
      </p>
      <details className="data-card">
        <summary>检索策略与属性筛选</summary>
        <label>
          查询策略
          <select
            value={strategy}
            onChange={(e) => {
              requestEpoch.current += 1;
              pending.current = false;
              setBusy(false);
              setAnswer(null);
              setStrategy(e.target.value);
            }}
          >
            <option value="HYBRID">混合检索（需真实模型配置）</option>
            <option value="KEYWORD">词面检索（审核原文摘录）</option>
            <option value="SEMANTIC">语义检索（需真实模型配置）</option>
            <option value="ATTRIBUTE">按属性筛选（须填写至少一项）</option>
          </select>
        </label>
        <label>
          主张属性 predicate_key
          <input
            value={predicateFilter}
            onChange={(e) => {
              requestEpoch.current += 1;
              pending.current = false;
              setBusy(false);
              setAnswer(null);
              setPredicateFilter(e.target.value);
            }}
          />
        </label>
        <label>
          对象 subject_entity_id（UUID）
          <input
            value={subjectFilter}
            onChange={(e) => {
              requestEpoch.current += 1;
              pending.current = false;
              setBusy(false);
              setAnswer(null);
              setSubjectFilter(e.target.value);
            }}
          />
        </label>
      </details>
      <div className="ask-workspace">
        <div className="ask-conversation">
          {!answer ? (
            <EmptyState
              title={
                busy
                  ? "正在检索发布知识与证据…"
                  : releases.length
                    ? "开始一次可信知识查询"
                    : "当前没有可查询的发布"
              }
              description={
                busy
                  ? "回答将绑定所选发布。你可以切换发布，旧查询结果不会混入当前上下文。"
                  : releases.length
                    ? "选择一个建议问题，或在下方输入自己的问题。回答将严格绑定当前发布。"
                    : "请先在发布中心完成质量校验与审批。"
              }
              primaryAction={
                releases.length && !busy ? (
                  <div className="suggested-questions">
                    {[
                      "有哪些关键风险需要关注？",
                      "这项结论依据了哪些资料？",
                      "当前知识中是否存在未解决冲突？",
                    ].map((item) => (
                      <button
                        type="button"
                        key={item}
                        onClick={() => {
                          setQuestion(item);
                          questionRef.current?.focus();
                        }}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                ) : !releases.length ? (
                  <a
                    className="btn"
                    href="/releases"
                    onClick={(event) => {
                      if (!onNavigate) return;
                      event.preventDefault();
                      onNavigate("releases");
                    }}
                  >
                    前往发布中心 →
                  </a>
                ) : undefined
              }
            />
          ) : (
            <article className="answer-card">
              <span className="question-bubble">{answer.question}</span>
              <h2>
                {answer.status === "REFUSED"
                  ? "证据不足，无法回答"
                  : "可信回答"}
              </h2>
              <p>{answer.direct_answer}</p>
              {explanation && (
                <div className="answer-explanation" role="note">
                  <strong>{explanation.title}</strong>
                  <p>{explanation.detail}</p>
                  <p>
                    <b>下一步：</b>
                    {explanation.next}
                  </p>
                </div>
              )}
              {answer.uncertainty && (
                <small>不确定性：{answer.uncertainty}</small>
              )}
            </article>
          )}
          <div className="ask-progress" role="status">
            {busy
              ? "正在查询，请稍候…"
              : answer
                ? "查询完成 · 回答与右侧证据对应同一发布"
                : "仅查询已发布知识，不读取草稿"}
          </div>
          <form
            className="ask-composer"
            aria-busy={busy}
            onSubmit={(event) => void ask(event)}
          >
            <label>
              你的问题 · Ctrl / ⌘ + Enter 发送
              <textarea
                ref={questionRef}
                value={question}
                disabled={busy || !releaseId}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    !event.nativeEvent.isComposing &&
                    event.key === "Enter" &&
                    (event.metaKey || event.ctrlKey)
                  ) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="向当前发布提问…"
              />
            </label>
            <button
              type="submit"
              className="primary"
              disabled={busy || !releaseId || !question.trim()}
            >
              {busy ? "查询中…" : "发送问题"}
            </button>
          </form>
        </div>
        <aside className="evidence-inspector">
          <h2>证据检查器</h2>
          {answer?.citations.length ? (
            answer.citations.map((item, index) => (
              <article key={item.id}>
                <strong>引用 {index + 1}</strong>
                <span>资料版本 {item.source_version_id.slice(0, 8)}</span>
                <span>证据位置 {item.source_anchor_id.slice(0, 8)}</span>
                <StatusPill value={item.status} />
                <a
                  className="btn"
                  href={sourcePreviewPath(
                    item.source_version_id,
                    item.source_anchor_id,
                  )}
                  onClick={(event) => {
                    if (!onNavigate) return;
                    event.preventDefault();
                    onNavigate(
                      sourcePreviewPath(
                        item.source_version_id,
                        item.source_anchor_id,
                      ),
                    );
                  }}
                >
                  查看原文定位
                </a>
              </article>
            ))
          ) : (
            <p>回答中的证据、来源位置和发布版本会显示在这里。</p>
          )}
          {answer && (
            <TechnicalDetails>
              <code>
                Release {answer.release_id} · 判定{" "}
                {answer.answer_reason ?? "未返回"}
              </code>
            </TechnicalDetails>
          )}
        </aside>
      </div>
    </section>
  );
}

function sourcePreviewPath(versionId: string, anchorId: string) {
  return `/source-versions/${encodeURIComponent(versionId)}/preview?${new URLSearchParams({ anchor_id: anchorId })}`;
}

export function GraphCenter({
  api,
  spaceId,
  onShowWikiGraph,
}: {
  api: NexweaveApi;
  spaceId: string;
  onShowWikiGraph?: () => void;
}) {
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [releaseId, setReleaseId] = useState("");
  const [start, setStart] = useState("");
  const [entities, setEntities] = useState<
    Array<{ id: string; display_name: string; type_key: string }>
  >([]);
  const [graph, setGraph] = useState<GraphTraverse | null>(null);
  const [error, setError] = useState("");
  const epoch = useRef(0);
  const [busy, setBusy] = useState(false);
  const retryReleases = useCallback(async () => {
    if (!spaceId) return;
    setError("");
    try {
      const result = await api.releases(spaceId);
      setReleases(result.items);
      setReleaseId((current) => current || result.items[0]?.id || "");
    } catch (cause) {
      setError(failure(cause));
    }
  }, [api, spaceId]);
  function resetGraph() {
    epoch.current++;
    setGraph(null);
    setError("");
    setBusy(false);
  }
  useEffect(() => {
    let active = true;
    setEntities([]);
    setStart("");
    if (!releaseId) return;
    void api
      .graphEntities(releaseId)
      .then((result) => {
        if (active) setEntities(result.items);
      })
      .catch((cause) => {
        if (active) setError(failure(cause));
      });
    return () => {
      active = false;
    };
  }, [api, releaseId]);
  useEffect(() => {
    const requests = epoch;
    let active = true;
    setReleases([]);
    setReleaseId("");
    setGraph(null);
    setStart("");
    setError("");
    setBusy(false);
    if (!spaceId) return;
    void api
      .releases(spaceId)
      .then((result) => {
        if (!active) return;
        setReleases(result.items);
        setReleaseId(result.items[0]?.id || "");
      })
      .catch((cause) => {
        if (active) setError(failure(cause));
      });
    return () => {
      active = false;
      requests.current++;
    };
  }, [api, spaceId]);
  async function traverse(event: FormEvent) {
    event.preventDefault();
    if (busy || !releaseId || !start.trim()) return;
    const current = ++epoch.current;
    setGraph(null);
    setBusy(true);
    setError("");
    try {
      const next = await api.graphTraverse(releaseId, start, 3);
      if (current === epoch.current) setGraph(next);
    } catch (cause) {
      if (current === epoch.current) setError(failure(cause));
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <h1>关系图谱</h1>
          <p>探索同一不可变发布中具有有效证据的正式知识关系。</p>
        </div>
        {onShowWikiGraph && (
          <button type="button" onClick={onShowWikiGraph}>
            查看页面知识图谱
          </button>
        )}
      </div>
      {error && <ErrorState message={error} onRetry={retryReleases} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="关系图谱需要在当前知识空间的已发布版本中进行探索。"
        />
      )}
      <form
        className="data-card m7-form"
        onSubmit={(event) => void traverse(event)}
      >
        <label>
          发布版本
          <select
            value={releaseId}
            onChange={(event) => {
              resetGraph();
              setReleaseId(event.target.value);
            }}
          >
            {releases.map((item) => (
              <option value={item.id} key={item.id}>
                {item.version}
              </option>
            ))}
          </select>
        </label>
        <label>
          选择已发布实体
          <select
            value={start}
            onChange={(event) => {
              resetGraph();
              setStart(event.target.value);
            }}
          >
            <option value="">请选择当前可见的冻结实体</option>
            {entities.map((entity) => (
              <option key={entity.id} value={entity.id}>
                {entity.display_name} · {entity.type_key}
              </option>
            ))}
          </select>
        </label>
        <label>
          起点实体
          <input
            value={start}
            onChange={(event) => {
              resetGraph();
              setStart(event.target.value);
            }}
            placeholder="输入实体标识"
          />
        </label>
        <button
          type="submit"
          className="primary"
          disabled={busy || !releaseId || !start}
        >
          遍历三跳
        </button>
      </form>
      {graph && (
        <div className="data-card">
          <h2>
            {graph.nodes.length} 节点 · {graph.edges.length} 关系
          </h2>
          <ul>
            {graph.nodes.map((node) => (
              <li key={String(node.id)}>
                {String(node.display_name ?? node.id)} ·{" "}
                {String(node.type_key ?? "实体")}
              </li>
            ))}
          </ul>
          {graph.truncated && (
            <p role="status">
              结果已达到显示上限，仅展示部分关系，请缩小查询范围。
            </p>
          )}
          {graph.edges.map((edge) => (
            <article className="graph-edge" key={edge.relation_id}>
              <strong>{edge.relation_type_key}</strong>
              <code>
                {edge.source_entity_id} → {edge.target_entity_id}
              </code>
              <small>
                深度 {edge.depth} · 证据 {edge.evidence_ids.length}
              </small>
            </article>
          ))}
        </div>
      )}
      {!graph && (
        <EmptyState
          title="选择起点开始探索"
          description="选定发布版本并输入起点实体，图谱会展示三跳以内的正式关系及其证据覆盖。"
        />
      )}
    </section>
  );
}
