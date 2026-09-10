import { useEffect, useRef, useState } from "react";
import { messageOf, type NexweaveApi } from "./api";
import type { ForecastKnowledgeContext } from "./livingTypes";
import type { KnowledgeRelease } from "./types";

export function ForecastKnowledge({
  api,
  spaceId,
  artifactId,
  onNavigate,
}: {
  api: NexweaveApi;
  spaceId: string;
  artifactId: string;
  onNavigate: (path: string) => void;
}) {
  const [releases, setReleases] = useState<KnowledgeRelease[]>([]);
  const [releaseId, setReleaseId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ForecastKnowledgeContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    const requests = generation;
    let active = true;
    setLoading(true);
    setReleases([]);
    setReleaseId("");
    setResult(null);
    setError("");
    if (!spaceId) {
      setLoading(false);
      return;
    }
    api
      .releases(spaceId)
      .then((r) => {
        if (active) setReleases(r.items);
      })
      .catch((e) => {
        if (active) setError(messageOf(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      requests.current++;
    };
  }, [api, spaceId, reload]);
  function invalidate() {
    generation.current++;
    setResult(null);
    setError("");
    setBusy(false);
  }
  async function search() {
    if (busy || !releaseId || !question.trim()) return;
    const current = ++generation.current;
    setBusy(true);
    setResult(null);
    setError("");
    try {
      const next = await api.forecastKnowledge(
        artifactId,
        releaseId,
        question.trim(),
      );
      if (current === generation.current) setResult(next);
    } catch (e) {
      if (current === generation.current) setError(messageOf(e));
    } finally {
      if (current === generation.current) setBusy(false);
    }
  }
  return (
    <section className="living-card" aria-label="已发布知识回接">
      <h2>查找已发布知识依据</h2>
      <p>
        为当前预测补充可核验的相关材料。选择固定知识版本；历史预测产物保持原样。
      </p>
      {loading ? (
        <p className="living-inline-status" role="status">
          正在读取已发布版本…
        </p>
      ) : (
        <>
          {!releases.length && (
            <div className="living-knowledge-empty">
              <span>◇</span>
              <p>当前空间没有可用的已发布知识版本。请先完成知识审核与发布。</p>
              <button type="button" onClick={() => onNavigate("releases")}>
                前往发布中心 →
              </button>
            </div>
          )}
          <form
            className="living-knowledge-form"
            onSubmit={(event) => {
              event.preventDefault();
              void search();
            }}
          >
            <label>
              <span>
                固定知识版本 <em>只读 · 不会自动切换</em>
              </span>
              <select
                aria-label="固定知识版本"
                value={releaseId}
                onChange={(e) => {
                  invalidate();
                  setReleaseId(e.target.value);
                }}
              >
                <option value="">请选择已发布版本</option>
                {releases.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.version} · {new Date(r.published_at).toLocaleString()}
                    {r.deprecated_at ? " · 已弃用" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>
                查找什么依据 <em>{question.length}/1000</em>
              </span>
              <textarea
                aria-label="查找什么依据"
                value={question}
                maxLength={1000}
                placeholder="输入需要核实的现象、故障模式、规程或历史案例关键词"
                onChange={(e) => {
                  invalidate();
                  setQuestion(e.target.value);
                }}
              />
            </label>
            <div className="living-knowledge-submit">
              <span>查询结果仅来自所选 Release 的可见证据</span>
              <button
                className="primary"
                type="submit"
                aria-label="检索已发布依据"
                disabled={busy || !releaseId || !question.trim()}
              >
                {busy ? "正在检索依据…" : "检索已发布依据 →"}
              </button>
            </div>
          </form>
        </>
      )}
      {error && (
        <div role="alert" className="living-error">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => {
              invalidate();
              setReload((n) => n + 1);
            }}
          >
            重新加载版本
          </button>
        </div>
      )}
      {result && (
        <div
          className={`living-knowledge-result ${result.status === "CITED_CONTEXT" ? "is-cited" : "is-insufficient"}`}
          aria-live="polite"
        >
          <div className="living-knowledge-result-head">
            <span className="living-tag">Released Knowledge · 本次回接</span>
            <strong>
              {result.items.length
                ? `${result.items.length} 条引用`
                : "无可用引用"}
            </strong>
          </div>
          <p>{result.explanation}</p>
          {result.release_deprecated && (
            <p className="living-warning">
              所选版本已弃用；这里只展示该历史版本，不自动切换。
            </p>
          )}
          {!result.items.length && (
            <p className="living-knowledge-no-citation">
              当前问题没有匹配到可见有效证据。预测结果保持不变，也不会将这次检索写回预测制品。
            </p>
          )}
          {result.items.map((item) => (
            <article key={item.citation.id}>
              <p>{item.statement}</p>
              <button
                type="button"
                onClick={() =>
                  onNavigate(
                    `/source-versions/${item.citation.source_version_id}/preview?anchor_id=${item.citation.source_anchor_id}`,
                  )
                }
              >
                查看原文定位
              </button>
              <details>
                <summary>引用与来源关系</summary>
                <p>
                  当前预测 → 本次相关知识检索 → 固定发布版本 → 主张 → 证据 →
                  原文定位
                </p>
                <p>
                  主张：{item.claim_id} · 证据：{item.citation.evidence_id}
                </p>
                <pre>{JSON.stringify(item.citation.locator, null, 2)}</pre>
              </details>
            </article>
          ))}
          {result.limitations.length > 0 && (
            <p className="living-form-help">{result.limitations.join(" ")}</p>
          )}
          <details>
            <summary>本次回接的版本与核验时间</summary>
            <p>核验时间：{new Date(result.checked_at).toLocaleString()}</p>
            <p>知识版本：{result.release_id}</p>
            <p className="living-hash">{result.release_checksum}</p>
            <p>预测产物：{result.artifact_id}</p>
            <p className="living-hash">{result.artifact_checksum}</p>
            <p>检索记录：{result.query_answer_id}</p>
          </details>
        </div>
      )}
    </section>
  );
}
