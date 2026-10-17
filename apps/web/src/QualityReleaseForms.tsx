import { useCallback, useEffect, useState, type FormEvent } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  ErrorState,
  GovernanceStepper,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  Claim,
  EvaluationCase,
  EvaluationRun,
  EvaluationSuite,
  GovernanceObject,
  KnowledgeRelease,
  Relation,
  ReleaseCandidate,
  SchemaVersion,
  WikiPage,
} from "./types";

type Props = { api: NexweaveApi; spaceId: string };
type DraftCase = EvaluationCase & { terms: string };
const newCase = (index: number): DraftCase => ({
  case_key: `case-${index}`,
  case_type: "ANSWERABLE",
  question: "",
  expected_claim_ids: [],
  expected_terms: [],
  expect_refusal: false,
  metadata: {},
  terms: "",
});
const refusalTypes = [
  "UNANSWERABLE",
  "COUNTERFACTUAL",
  "INSUFFICIENT_EVIDENCE",
];
const toggle = (values: string[], id: string) =>
  values.includes(id) ? values.filter((v) => v !== id) : [...values, id];

export function QualityCenter(props: Props) {
  return <QualityView key={props.spaceId} {...props} />;
}

function QualityView({ api, spaceId }: Props) {
  const [suites, setSuites] = useState<EvaluationSuite[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [candidates, setCandidates] = useState<ReleaseCandidate[]>([]);
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [schemaId, setSchemaId] = useState("");
  const [suiteKey, setSuiteKey] = useState("");
  const [version, setVersion] = useState(1);
  const [name, setName] = useState("");
  const [cases, setCases] = useState<DraftCase[]>([newCase(1)]);
  const [suiteId, setSuiteId] = useState("");
  const [target, setTarget] = useState("");
  const [strategy, setStrategy] = useState("KEYWORD");
  const [predicate, setPredicate] = useState("");
  const [subject, setSubject] = useState("");
  const [selectedRun, setSelectedRun] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) return;
    try {
      const [s, sc, cl, ca, re, ru] = await Promise.all([
        api.evaluationSuites(spaceId),
        api.schemas(spaceId),
        api.claims(spaceId),
        api.releaseCandidates(spaceId),
        api.releases(spaceId),
        api.evaluationRuns(spaceId),
      ]);
      setSuites(s);
      setSchemas(sc.items.filter((v) => v.status === "PUBLISHED"));
      setClaims(cl.items);
      setCandidates(ca.items);
      setReleases(re.items);
      setRuns(ru);
      setError("");
    } catch (cause) {
      setError(messageOf(cause));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  const pending = runs.some((r) => ["CREATED", "RUNNING"].includes(r.status));
  useEffect(() => {
    if (!pending) return;
    let active = true;
    const timer = window.setInterval(() => {
      void api
        .evaluationRuns(spaceId)
        .then((r) => {
          if (active) setRuns(r);
        })
        .catch((cause) => {
          if (active) setError(messageOf(cause));
        });
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [api, spaceId, pending]);
  const targets = [
    ...candidates.map((c) => ({ ...c, kind: "RELEASE_CANDIDATE" })),
    ...releases.map((r) => ({ ...r, kind: "RELEASE" })),
  ];
  const selectedTarget = targets.find((t) => `${t.kind}:${t.id}` === target);
  const selected = runs.find((r) => r.id === selectedRun);
  function update(index: number, values: Partial<DraftCase>) {
    setCases((all) =>
      all.map((c, i) => (i === index ? { ...c, ...values } : c)),
    );
  }
  function copy(suite: EvaluationSuite) {
    setSchemaId(suite.schema_version_id);
    setSuiteKey(suite.suite_key);
    setVersion(suite.version + 1);
    setName(suite.name);
    setCases(
      suite.cases.map((c) => ({ ...c, terms: c.expected_terms.join("\n") })),
    );
    setNotice("已载入新版本草稿；修改后保存会追加版本，原问题集保持不变。");
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy || !schemaId) return;
    setBusy(true);
    try {
      await api.createEvaluationSuite(spaceId, {
        schema_version_id: schemaId,
        suite_key: suiteKey,
        version,
        name,
        minimum_pass_rate: 100,
        cases: cases.map(({ terms, ...c }) => ({
          ...c,
          expected_terms: terms
            .split("\n")
            .map((t) => t.trim())
            .filter(Boolean),
        })),
      });
      await load();
      setNotice(
        "问题集新版本已保存，门槛保持 100%；请明确选择目标后运行真实评估。",
      );
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function run(event: FormEvent) {
    event.preventDefault();
    if (busy || !selectedTarget || !suiteId) return;
    setBusy(true);
    try {
      const result = await api.createEvaluationRun(spaceId, {
        suite_id: suiteId,
        target_type: selectedTarget.kind,
        target_id: selectedTarget.id,
        retrieval_strategy: strategy,
        retrieval_config: {
          top_k: 5,
          filters: {
            ...(predicate.trim() ? { predicate_key: predicate.trim() } : {}),
            ...(subject.trim() ? { subject_entity_id: subject.trim() } : {}),
          },
        },
      });
      setRuns((current) => [result, ...current]);
      setSelectedRun(result.id);
      setError("");
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="质量中心"
        description="维护多题版本化业务问题集，使用与真实提问相同的流程，逐题核对答案、召回、引用与拒答。"
      />
      <GovernanceStepper current="quality" />
      {error && <ErrorState message={error} onRetry={load} />}
      {notice && <p role="status">{notice}</p>}
      <form className="data-card m7-form" onSubmit={(e) => void save(e)}>
        <h2>维护回归问题集</h2>
        <label>
          知识模型 Schema
          <select
            required
            value={schemaId}
            onChange={(e) => {
              setSchemaId(e.target.value);
              setCases([newCase(1)]);
            }}
          >
            <option value="">请选择已发布 Schema</option>
            {schemas.map((s) => (
              <option key={s.id} value={s.id}>
                {s.schema_key} · {s.semantic_version}
              </option>
            ))}
          </select>
        </label>
        <label>
          问题集标识（例如 business/pump-questions）
          <input
            required
            pattern="[a-z][a-z0-9.-]{1,62}/[a-z][a-z0-9-]{0,62}"
            value={suiteKey}
            onChange={(e) => setSuiteKey(e.target.value)}
          />
        </label>
        <label>
          问题集名称
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          追加版本号
          <input
            type="number"
            required
            min={1}
            value={version}
            onChange={(e) => setVersion(Number(e.target.value))}
          />
        </label>
        {cases.map((c, index) => (
          <fieldset key={index}>
            <legend>问题 {index + 1}</legend>
            <label>
              题目标识
              <input
                required
                value={c.case_key}
                onChange={(e) => update(index, { case_key: e.target.value })}
              />
            </label>
            <label>
              自然问句
              <textarea
                required
                value={c.question}
                onChange={(e) => update(index, { question: e.target.value })}
              />
            </label>
            <label>
              问题类型
              <select
                value={c.case_type}
                onChange={(e) => {
                  const refused = refusalTypes.includes(e.target.value);
                  update(index, {
                    case_type: e.target.value,
                    expect_refusal: refused,
                    expected_refusal_reason: null,
                    ...(refused ? { expected_claim_ids: [], terms: "" } : {}),
                  });
                }}
              >
                <option value="ANSWERABLE">应有依据地回答</option>
                <option value="MULTI_SOURCE">需要多个来源</option>
                <option value="CONFLICT">冲突问题</option>
                <option value="COUNTERFACTUAL">错误对象或反事实，应拒答</option>
                <option value="INSUFFICIENT_EVIDENCE">证据不足，应拒答</option>
                <option value="UNANSWERABLE">范围之外，应拒答</option>
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={c.expect_refusal}
                disabled={refusalTypes.includes(c.case_type)}
                onChange={(e) =>
                  update(index, {
                    expect_refusal: e.target.checked,
                    expected_refusal_reason: null,
                  })
                }
              />
              预期拒答
            </label>
            {c.expect_refusal ? (
              <label>
                拒答条件
                <select
                  value={c.expected_refusal_reason ?? ""}
                  onChange={(e) =>
                    update(index, {
                      expected_refusal_reason: (e.target.value ||
                        null) as EvaluationCase["expected_refusal_reason"],
                    })
                  }
                >
                  <option value="">任意证据不足拒答</option>
                  <option value="NO_MATCHING_KNOWLEDGE">
                    没有召回匹配知识
                  </option>
                  <option value="EVIDENCE_UNAVAILABLE">
                    已召回但证据或权限失效
                  </option>
                </select>
              </label>
            ) : (
              <>
                <label>
                  预期答案片段（每行一条，必须全部出现在实际回答中）
                  <textarea
                    value={c.terms}
                    onChange={(e) => update(index, { terms: e.target.value })}
                  />
                </label>
                <fieldset>
                  <legend>必须引用的已审核 Claim</legend>
                  {claims
                    .filter((v) => v.schema_version_id === schemaId)
                    .map((cl) => (
                      <label key={cl.id}>
                        <input
                          type="checkbox"
                          checked={c.expected_claim_ids.includes(cl.id)}
                          onChange={() =>
                            update(index, {
                              expected_claim_ids: toggle(
                                c.expected_claim_ids,
                                cl.id,
                              ),
                            })
                          }
                        />
                        {cl.statement}
                      </label>
                    ))}
                </fieldset>
                {!c.terms.trim() && !c.expected_claim_ids.length && (
                  <p>
                    应回答题必须至少指定预期答案片段或
                    Claim，不能以空期望计作通过。
                  </p>
                )}
              </>
            )}
            <button
              type="button"
              disabled={cases.length === 1}
              onClick={() =>
                setCases((all) => all.filter((_, i) => i !== index))
              }
            >
              移除此题
            </button>
          </fieldset>
        ))}
        <button
          type="button"
          onClick={() => setCases((all) => [...all, newCase(all.length + 1)])}
        >
          添加问题
        </button>
        <button
          className="primary"
          disabled={
            busy ||
            !schemaId ||
            cases.some(
              (c) =>
                !c.question.trim() ||
                (!c.expect_refusal &&
                  !c.terms.trim() &&
                  !c.expected_claim_ids.length),
            )
          }
        >
          保存问题集新版本（100% 门槛）
        </button>
      </form>
      <section className="data-card">
        <h2>现有问题集</h2>
        {suites.map((s) => (
          <article className="list-row" key={s.id}>
            <strong>
              {s.name} · v{s.version} · {s.cases.length} 题
            </strong>
            <button type="button" onClick={() => copy(s)}>
              载入并维护下一版
            </button>
            <TechnicalDetails>
              <pre>{JSON.stringify(s.cases, null, 2)}</pre>
            </TechnicalDetails>
          </article>
        ))}
      </section>
      <form className="data-card m7-form" onSubmit={(e) => void run(e)}>
        <h2>运行真实问答评估</h2>
        <label>
          评估目标
          <select
            required
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setSuiteId("");
            }}
          >
            <option value="">请选择固定候选或发布</option>
            {targets.map((t) => (
              <option key={`${t.kind}:${t.id}`} value={`${t.kind}:${t.id}`}>
                {t.kind === "RELEASE" ? "已发布" : "候选"} · {t.version} ·{" "}
                {t.status}
              </option>
            ))}
          </select>
        </label>
        <label>
          问题集与版本
          <select
            required
            value={suiteId}
            onChange={(e) => setSuiteId(e.target.value)}
          >
            <option value="">请选择与目标 Schema 一致的问题集</option>
            {suites
              .filter(
                (s) =>
                  s.schema_version_id === selectedTarget?.schema_version_id,
              )
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · v{s.version}
                </option>
              ))}
          </select>
        </label>
        <label>
          检索策略
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
          >
            {["HYBRID", "KEYWORD", "SEMANTIC", "ATTRIBUTE"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          属性筛选 predicate_key（可选）
          <input
            value={predicate}
            onChange={(e) => setPredicate(e.target.value)}
          />
        </label>
        <label>
          对象筛选 subject_entity_id（UUID，可选）
          <input value={subject} onChange={(e) => setSubject(e.target.value)} />
        </label>
        <button
          className="primary"
          disabled={
            busy ||
            !suiteId ||
            !selectedTarget ||
            (strategy === "ATTRIBUTE" && !predicate.trim() && !subject.trim())
          }
        >
          执行真实问答评估
        </button>
      </form>
      <section className="data-card">
        <h2>评估执行与逐题结果</h2>
        <p>
          展示最近 100
          次且当前仍有权读取的执行；来源失效或无权限的范围不会返回历史答案。
        </p>
        {runs.map((r) => (
          <button
            className="list-row"
            type="button"
            key={r.id}
            onClick={() => setSelectedRun(r.id)}
          >
            <strong>{r.id.slice(-8)}</strong>
            <StatusPill value={r.status} />
            <span>
              {r.result_visibility === "METADATA_ONLY"
                ? "当前范围不可读，历史答案已隐藏"
                : r.gate_passed == null
                  ? "尚未形成结论"
                  : r.gate_passed
                    ? "历史执行门禁通过"
                    : "历史执行门禁未通过"}
            </span>
          </button>
        ))}
        {selected && (
          <>
            {selected.result_visibility === "METADATA_ONLY" ? (
              <p role="status">
                来源或权限当前不可用，不能把被隐藏的历史分数当作当前质量通过。执行原记录保持不变。
              </p>
            ) : (
              <p>
                本次通过率 {String(selected.metrics.pass_rate ?? "—")}% ·{" "}
                {String(selected.metrics.passed ?? "—")} /{" "}
                {String(selected.metrics.cases ?? "—")} 题
              </p>
            )}
            <TechnicalDetails>
              <pre>{JSON.stringify(selected.metrics, null, 2)}</pre>
            </TechnicalDetails>
            {selected.results.map((r) => (
              <article className="data-card" key={r.case_key}>
                <h3>
                  {r.case_key} · {r.passed ? "通过" : "未通过"}
                </h3>
                <blockquote>{r.details.question}</blockquote>
                <StatusPill value={r.answer_status} />
                <p>{r.details.actual?.direct_answer ?? "执行未产生答案"}</p>
                <p>依据：{r.details.actual?.answer_reason ?? r.error_code}</p>
                <p>
                  目标 Claim 召回：
                  {r.details.expected_claim_ids?.length
                    ? r.details.scoring?.expected_claims_retrieved
                      ? "符合期望"
                      : "未符合期望"
                    : "未指定 Claim"}{" "}
                  · 引用：
                  {r.details.expected_claim_ids?.length
                    ? r.details.scoring?.expected_claims_cited
                      ? "符合期望"
                      : "未符合期望"
                    : "未指定 Claim"}
                </p>
                <p>
                  答案片段：
                  {r.details.expected_terms?.length
                    ? r.details.scoring?.terms_in_answer
                      ? "全部匹配"
                      : "未全部匹配"
                    : "未指定片段"}{" "}
                  · 拒答判断：
                  {r.details.scoring?.refusal_matches
                    ? "符合期望"
                    : "未符合期望"}
                  {r.details.scoring?.expected_refusal_reason
                    ? ` · 原因 ${r.details.scoring.refusal_reason_matches ? "匹配" : "未匹配"}`
                    : ""}
                </p>
                {r.details.actual?.citations.map((c) => (
                  <a
                    key={c.evidence_id}
                    href={`/source-versions/${c.source_version_id}/preview?anchor_id=${c.source_anchor_id}`}
                  >
                    核对引用原文 · {c.evidence_id.slice(-8)}
                  </a>
                ))}
                <TechnicalDetails>
                  <pre>
                    {JSON.stringify(
                      {
                        scoring: r.details.scoring,
                        retrieval: r.details.actual?.retrieval_trace,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </TechnicalDetails>
              </article>
            ))}
          </>
        )}
      </section>
    </section>
  );
}

export function ReleaseCenter(props: Props) {
  return <ReleaseView key={props.spaceId} {...props} />;
}

function ReleaseView({ api, spaceId }: Props) {
  const [candidates, setCandidates] = useState<ReleaseCandidate[]>([]);
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [suites, setSuites] = useState<EvaluationSuite[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [pages, setPages] = useState<WikiPage[]>([]);
  const [prompts, setPrompts] = useState<GovernanceObject[]>([]);
  const [models, setModels] = useState<GovernanceObject[]>([]);
  const [schemaId, setSchemaId] = useState("");
  const [suiteId, setSuiteId] = useState("");
  const [promptId, setPromptId] = useState("");
  const [modelId, setModelId] = useState("");
  const [retrievalStrategy, setRetrievalStrategy] = useState("KEYWORD");
  const [embeddingId, setEmbeddingId] = useState("");
  const [claimIds, setClaimIds] = useState<string[]>([]);
  const [relationIds, setRelationIds] = useState<string[]>([]);
  const [wikiIds, setWikiIds] = useState<string[]>([]);
  const [version, setVersion] = useState("");
  const [notes, setNotes] = useState("");
  const [approvalReason, setApprovalReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [configurationError, setConfigurationError] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) return;
    try {
      const [core, options] = await Promise.allSettled([
        Promise.all([
          api.releaseCandidates(spaceId),
          api.releases(spaceId),
          api.evaluationSuites(spaceId),
          api.schemas(spaceId),
          api.claims(spaceId),
          api.relations(spaceId),
          api.wikiPages(spaceId),
        ]),
        api.executionOptions(spaceId),
      ]);
      if (core.status === "rejected") throw core.reason;
      const [ca, re, su, sc, cl, rel, wp] = core.value;
      setCandidates(ca.items);
      setReleases(re.items);
      setSuites(su);
      setSchemas(sc.items.filter((s) => s.status === "PUBLISHED"));
      setClaims(cl.items);
      setRelations(rel.items);
      setPages(wp.items);
      setPrompts(
        options.status === "fulfilled" ? options.value.prompt_versions : [],
      );
      setModels(
        options.status === "fulfilled" ? options.value.model_profiles : [],
      );
      setConfigurationError(
        options.status === "rejected"
          ? `创建配置暂不可用：${messageOf(options.reason)}`
          : "",
      );
      setError("");
    } catch (cause) {
      setError(messageOf(cause));
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);
  const pending = candidates.some((c) =>
    ["DRAFT", "VALIDATING", "APPROVED", "PUBLISHING"].includes(c.status),
  );
  useEffect(() => {
    if (!pending) return;
    let active = true;
    const timer = window.setInterval(() => {
      void Promise.all([api.releaseCandidates(spaceId), api.releases(spaceId)])
        .then(([c, r]) => {
          if (active) {
            setCandidates(c.items);
            setReleases(r.items);
          }
        })
        .catch((cause) => {
          if (active) setError(messageOf(cause));
        });
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [api, spaceId, pending]);
  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy || !schemaId || !suiteId || !promptId || !modelId) return;
    setBusy(true);
    try {
      await api.createReleaseCandidate(spaceId, {
        version,
        schema_version_id: schemaId,
        prompt_version_id: promptId,
        model_profile_id: modelId,
        evaluation_suite_id: suiteId,
        claim_ids: claimIds,
        relation_ids: relationIds,
        wiki_page_version_ids: wikiIds,
        index_config: {
          version: "r1-query-v3",
          retrieval_strategy: retrievalStrategy,
          ...(embeddingId ? { embedding_model_profile_id: embeddingId } : {}),
        },
        notes,
      });
      await load();
      setNotice(
        "所选范围已冻结为候选，正在执行真实质量门禁；发布仍需独立批准。",
      );
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  async function publish(candidate: ReleaseCandidate) {
    if (busy || !approvalReason.trim()) return;
    setBusy(true);
    try {
      await api.publishReleaseCandidate(candidate.id, approvalReason.trim());
      await load();
      setNotice(
        "批准已记录，后台仍会复核当前权限、来源和质量；请等待正式发布状态。",
      );
      setApprovalReason("");
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="发布中心"
        description="明确选择配置和逐条内容，冻结候选后复查实际质量门禁，由独立批准人发布。"
      />
      <GovernanceStepper current="releases" />
      {error && <ErrorState message={error} onRetry={load} />}
      {notice && <p role="status">{notice}</p>}
      {configurationError && <p role="status">{configurationError}</p>}
      <form className="data-card m7-form" onSubmit={(e) => void create(e)}>
        <h2>创建发布候选</h2>
        <label>
          SemVer
          <input
            required
            placeholder="例如 1.0.0"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
          />
        </label>
        <label>
          发布 Schema
          <select
            required
            value={schemaId}
            onChange={(e) => {
              setSchemaId(e.target.value);
              setSuiteId("");
              setClaimIds([]);
              setRelationIds([]);
              setWikiIds([]);
            }}
          >
            <option value="">请明确选择 Schema</option>
            {schemas.map((s) => (
              <option key={s.id} value={s.id}>
                {s.schema_key} · {s.semantic_version}
              </option>
            ))}
          </select>
        </label>
        <label>
          质量套件与版本
          <select
            required
            value={suiteId}
            onChange={(e) => setSuiteId(e.target.value)}
          >
            <option value="">请选择相同 Schema 的套件</option>
            {suites
              .filter((s) => s.schema_version_id === schemaId)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · v{s.version} · {s.cases.length} 题
                </option>
              ))}
          </select>
        </label>
        <label>
          Prompt 版本
          <select
            required
            value={promptId}
            onChange={(e) => setPromptId(e.target.value)}
          >
            <option value="">请选择 Prompt</option>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>
                {String(p.prompt_key ?? p.name ?? p.id)} ·{" "}
                {String(p.revision ?? "")}
              </option>
            ))}
          </select>
        </label>
        <label>
          模型配置
          <select
            required
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          >
            <option value="">请选择模型配置</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {String(m.name ?? m.id)} · {String(m.provider ?? "")}
              </option>
            ))}
          </select>
        </label>
        <label>
          发布检索策略
          <select
            value={retrievalStrategy}
            onChange={(e) => setRetrievalStrategy(e.target.value)}
          >
            <option value="KEYWORD">词面检索（无需模型）</option>
            <option value="HYBRID">混合检索（需真实 embedding）</option>
            <option value="SEMANTIC">语义检索（需真实 embedding）</option>
          </select>
        </label>
        {retrievalStrategy !== "KEYWORD" && (
          <label>
            真实 embedding 配置
            <select
              required
              value={embeddingId}
              onChange={(e) => setEmbeddingId(e.target.value)}
            >
              <option value="">请选择已配置的真实 embedding 模型</option>
              {models
                .filter(
                  (m) =>
                    m.provider === "openai-compatible" &&
                    (m.config as Record<string, unknown> | undefined)
                      ?.capability === "embedding",
                )
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {String(m.name)} · {String(m.model_name)}
                  </option>
                ))}
            </select>
          </label>
        )}
        <fieldset>
          <legend>发布 Claim（默认不选）</legend>
          {claims
            .filter((c) => c.schema_version_id === schemaId)
            .map((c) => (
              <label key={c.id}>
                <input
                  type="checkbox"
                  checked={claimIds.includes(c.id)}
                  onChange={() => setClaimIds((all) => toggle(all, c.id))}
                />
                {c.statement}
              </label>
            ))}
        </fieldset>
        <fieldset>
          <legend>发布 Relation（默认不选）</legend>
          {relations
            .filter((r) => r.schema_version_id === schemaId)
            .map((r) => (
              <label key={r.id}>
                <input
                  type="checkbox"
                  checked={relationIds.includes(r.id)}
                  onChange={() => setRelationIds((all) => toggle(all, r.id))}
                />
                {r.relation_type_key} ·{" "}
                {pages.find((p) => p.primary_entity_id === r.source_entity_id)
                  ?.title ?? r.source_entity_id}{" "}
                →{" "}
                {pages.find((p) => p.primary_entity_id === r.target_entity_id)
                  ?.title ?? r.target_entity_id}
              </label>
            ))}
        </fieldset>
        <fieldset>
          <legend>发布 Wiki 当前版本（默认不选，提交时冻结）</legend>
          {pages
            .filter(
              (p) => p.schema_version_id === schemaId && p.current_version_id,
            )
            .map((p) => (
              <label key={p.id}>
                <input
                  type="checkbox"
                  checked={wikiIds.includes(p.current_version_id!)}
                  onChange={() =>
                    setWikiIds((all) => toggle(all, p.current_version_id!))
                  }
                />
                {p.title} · {p.current_version_id?.slice(-8)}
              </label>
            ))}
        </fieldset>
        <p>
          已选 {claimIds.length} 条 Claim、{relationIds.length} 条 Relation、
          {wikiIds.length} 个 Wiki 版本。
        </p>
        <label>
          范围说明与发布说明
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button
          className="primary"
          disabled={
            busy ||
            !schemaId ||
            !suiteId ||
            !promptId ||
            !modelId ||
            !(claimIds.length + relationIds.length + wikiIds.length)
          }
        >
          按所选范围创建候选并验证
        </button>
      </form>
      <section className="data-card">
        <h2>候选与门禁</h2>
        <label>
          独立批准的实质理由
          <textarea
            value={approvalReason}
            onChange={(e) => setApprovalReason(e.target.value)}
          />
        </label>
        {candidates.map((c) => (
          <article className="list-row" key={c.id}>
            <strong>{c.version}</strong>
            <StatusPill value={c.status} />
            <p>
              {c.gate_summary.evaluation_passed === true
                ? "真实问答评估通过"
                : "真实问答评估尚未通过"}{" "}
              ·{" "}
              {c.gate_summary.traceability_percent === 100
                ? "证据追溯完整"
                : "核对追溯门禁"}
            </p>
            <p>
              套件{" "}
              {suites.find((s) => s.id === c.evaluation_suite_id)?.name ??
                c.evaluation_suite_id}
            </p>
            {c.lint_findings.map((f) => (
              <p key={f.id}>
                {f.blocking ? "阻断" : "提示"}：{f.message}
              </p>
            ))}
            <TechnicalDetails>
              <pre>
                {JSON.stringify(
                  { manifest: c.manifest, gate: c.gate_summary },
                  null,
                  2,
                )}
              </pre>
              <code>{c.manifest_checksum}</code>
            </TechnicalDetails>
            {c.status === "PENDING_APPROVAL" && (
              <button
                type="button"
                disabled={busy || !approvalReason.trim()}
                onClick={() => void publish(c)}
              >
                批准此候选并发布
              </button>
            )}
            {c.gate_summary.evaluation_run_id != null && (
              <p>在质量中心可按候选查看逐题实际结果。</p>
            )}
          </article>
        ))}
      </section>
      <section className="data-card">
        <h2>不可变发布历史</h2>
        {releases.map((r) => (
          <article key={r.id} className="list-row">
            <strong>{r.version}</strong>
            <StatusPill value={r.status} />
            <small>{new Date(r.published_at).toLocaleString()}</small>
            <TechnicalDetails>
              <code>{r.manifest_checksum}</code>
            </TechnicalDetails>
          </article>
        ))}
      </section>
    </section>
  );
}
