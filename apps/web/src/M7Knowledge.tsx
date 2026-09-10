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
  GovernanceStepper,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  Claim,
  EvaluationSuite,
  GovernanceObject,
  GraphTraverse,
  KnowledgeRelease,
  QueryAnswer,
  ReleaseCandidate,
  SchemaVersion,
} from "./types";

function failure(cause: unknown) {
  return messageOf(cause, "请求未能安全完成。");
}

export function QualityCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [suites, setSuites] = useState<EvaluationSuite[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [question, setQuestion] = useState(
    "当前 Release 是否包含这条已审核主张？",
  );
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setSuites([]);
      setSchemas([]);
      setClaims([]);
      setError("");
      return;
    }
    try {
      const [nextSuites, nextSchemas, nextClaims] = await Promise.all([
        api.evaluationSuites(spaceId),
        api.schemas(spaceId),
        api.claims(spaceId),
      ]);
      setSuites(nextSuites);
      setSchemas(
        nextSchemas.items.filter((item) => item.status === "PUBLISHED"),
      );
      setClaims(nextClaims.items);
      setError("");
    } catch (cause) {
      setError(failure(cause));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    const schema = schemas[0];
    if (!schema) return;
    try {
      await api.createEvaluationSuite(spaceId, {
        schema_version_id: schema.id,
        suite_key: `space/quality-${Date.now()}`,
        version: 1,
        name: "Release regression gate",
        minimum_pass_rate: 100,
        cases: [
          {
            case_key: "approved-claim",
            case_type: claims[0] ? "ANSWERABLE" : "INSUFFICIENT_EVIDENCE",
            question,
            expected_claim_ids: claims[0] ? [claims[0].id] : [],
            expected_terms: [],
            expect_refusal: !claims[0],
            metadata: { created_from: "quality-center" },
          },
        ],
      });
      await load();
    } catch (cause) {
      setError(failure(cause));
    }
  }

  return (
    <section className="content-page">
      <PageHeader
        title="质量中心"
        description="以标准问题集验证已审核知识，质量问题与门禁结果都可复查。"
      />
      <GovernanceStepper current="quality" />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="质量问题集必须绑定到当前知识空间的已审核知识。"
        />
      )}
      <form
        className="data-card m7-form"
        onSubmit={(event) => void create(event)}
      >
        <h2>新建回归问题集</h2>
        <label>
          验证问题
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>
        <button className="primary" type="submit" disabled={!schemas.length}>
          以当前已审核知识创建
        </button>
      </form>
      <div className="data-card">
        <h2>问题集</h2>
        {suites.map((suite) => (
          <article className="list-row" key={suite.id}>
            <strong>{suite.name}</strong>
            <small>
              {suite.suite_key} · v{suite.version} ·{" "}
              <StatusPill value={suite.status} />
            </small>
            <span>
              {suite.cases.length} 题 · 门槛 {suite.minimum_pass_rate}%
            </span>
          </article>
        ))}
        {!suites.length && (
          <EmptyState
            title="还没有质量问题集"
            description="先准备已发布的知识模型和已审核主张，再创建第一组发布前验证问题。"
          />
        )}
      </div>
    </section>
  );
}

export function ReleaseCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [candidates, setCandidates] = useState<ReleaseCandidate[]>([]);
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [suites, setSuites] = useState<EvaluationSuite[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [prompts, setPrompts] = useState<GovernanceObject[]>([]);
  const [models, setModels] = useState<GovernanceObject[]>([]);
  const [version, setVersion] = useState("1.0.0");
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setCandidates([]);
      setReleases([]);
      setSuites([]);
      setSchemas([]);
      setClaims([]);
      setPrompts([]);
      setModels([]);
      setError("");
      return;
    }
    try {
      const [
        nextCandidates,
        nextReleases,
        nextSuites,
        nextSchemas,
        nextClaims,
        nextPrompts,
        nextModels,
      ] = await Promise.all([
        api.releaseCandidates(spaceId),
        api.releases(spaceId),
        api.evaluationSuites(spaceId),
        api.schemas(spaceId),
        api.claims(spaceId),
        api.listGovernance("prompt-versions"),
        api.listGovernance("model-profiles"),
      ]);
      setCandidates(nextCandidates.items);
      setReleases(nextReleases.items);
      setSuites(nextSuites);
      setSchemas(
        nextSchemas.items.filter((item) => item.status === "PUBLISHED"),
      );
      setClaims(nextClaims.items);
      setPrompts(nextPrompts.items);
      setModels(nextModels.items);
      setError("");
    } catch (cause) {
      setError(failure(cause));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (
      !schemas[0] ||
      !suites[0] ||
      !prompts[0] ||
      !models[0] ||
      !claims.length
    )
      return;
    try {
      await api.createReleaseCandidate(spaceId, {
        version,
        schema_version_id: schemas[0].id,
        prompt_version_id: prompts[0].id,
        model_profile_id: models[0].id,
        evaluation_suite_id: suites[0].id,
        claim_ids: claims.map((item) => item.id),
        relation_ids: [],
        wiki_page_version_ids: [],
        index_config: {
          version: "m7-r1",
          fusion: "rrf",
          vector_dimensions: 16,
        },
        notes: "Created from Release Center",
      });
      await load();
    } catch (cause) {
      setError(failure(cause));
    }
  }

  async function publish(candidate: ReleaseCandidate) {
    if (publishing) return;
    setPublishing(candidate.id);
    try {
      await api.publishReleaseCandidate(
        candidate.id,
        "Release Center Publisher approval",
      );
      await load();
    } catch (cause) {
      setError(failure(cause));
    } finally {
      setPublishing("");
    }
  }

  return (
    <section className="content-page">
      <PageHeader
        title="发布中心"
        description="创建发布候选，完成质量校验与独立审批后，生成不可变知识版本。"
      />
      <GovernanceStepper current="releases" />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="发布候选必须绑定到当前知识空间的模型、质量门禁与已审核主张。"
        />
      )}
      <form
        className="data-card m7-form"
        onSubmit={(event) => void create(event)}
      >
        <h2>创建发布候选</h2>
        <label>
          SemVer
          <input
            value={version}
            onChange={(event) => setVersion(event.target.value)}
          />
        </label>
        <button
          className="primary"
          type="submit"
          disabled={!claims.length || !suites.length}
        >
          固定已审核知识
        </button>
      </form>
      <div className="m7-grid">
        <div className="data-card">
          <h2>候选与门禁</h2>
          {candidates.map((item) => (
            <article className="list-row" key={item.id}>
              <strong>{item.version}</strong>
              <StatusPill value={item.status} />
              <span>质量校验结果已记录</span>
              <TechnicalDetails>
                <code>{item.manifest_checksum}</code>
                <pre>{JSON.stringify(item.gate_summary, null, 2)}</pre>
              </TechnicalDetails>
              {item.status === "PENDING_APPROVAL" && (
                <button
                  type="button"
                  disabled={Boolean(publishing)}
                  onClick={() => void publish(item)}
                >
                  {publishing === item.id ? "发布中…" : "批准并发布"}
                </button>
              )}
            </article>
          ))}
          {!candidates.length && (
            <EmptyState
              title="还没有发布候选"
              description="质量问题集、知识模型与已审核主张准备完成后，可在上方创建候选版本。"
            />
          )}
        </div>
        <div className="data-card">
          <h2>不可变历史</h2>
          {releases.map((item) => (
            <article className="list-row" key={item.id}>
              <strong>{item.version}</strong>
              <small>
                <StatusPill value={item.status} /> ·{" "}
                {new Date(item.published_at).toLocaleString()}
              </small>
              <TechnicalDetails>
                <code>{item.manifest_checksum}</code>
              </TechnicalDetails>
            </article>
          ))}
          {!releases.length && (
            <EmptyState
              title="还没有正式发布"
              description="候选版本通过质量门禁并获得独立审批后，会进入不可变历史。"
            />
          )}
        </div>
      </div>
    </section>
  );
}

export function AskCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [releaseId, setReleaseId] = useState("");
  const [question, setQuestion] = useState("");
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
        strategy: "HYBRID",
        top_k: 5,
        filters: {},
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
                  <a className="btn" href="/releases">
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
              </article>
            ))
          ) : (
            <p>回答中的证据、来源位置和发布版本会显示在这里。</p>
          )}
          {answer && (
            <TechnicalDetails>
              <code>Release {answer.release_id}</code>
            </TechnicalDetails>
          )}
        </aside>
      </div>
    </section>
  );
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
