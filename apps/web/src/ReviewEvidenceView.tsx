import { useRef, useState } from "react";

import { messageOf, NexweaveApi } from "./api";
import { ErrorState, StatusPill, TechnicalDetails } from "./design-system/ui";
import type { PreviewResponse, ReviewTarget } from "./types";
import { targetText } from "./reviewText";

export function ReviewEvidenceView({
  api,
  target,
}: {
  api: NexweaveApi;
  target: ReviewTarget;
}) {
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const epoch = useRef(0);
  async function open(version: string, anchor: string) {
    const request = ++epoch.current;
    setLoading(true);
    setPreview(null);
    setError("");
    try {
      const result = await api.sourcePreview(version, anchor);
      if (request === epoch.current) setPreview(result);
    } catch (cause) {
      if (request === epoch.current) setError(messageOf(cause));
    } finally {
      if (request === epoch.current) setLoading(false);
    }
  }
  return (
    <section aria-label="被审内容与证据">
      <h3>被审正文</h3>
      <blockquote>{targetText(target)}</blockquote>
      {target.content.object_value !== undefined && (
        <pre>{JSON.stringify(target.content.object_value, null, 2)}</pre>
      )}
      {target.content.source_entity_id !== undefined && (
        <p>
          方向：
          {target.entity_labels?.[String(target.content.source_entity_id)] ??
            String(target.content.source_entity_id)}{" "}
          →{" "}
          {target.entity_labels?.[String(target.content.target_entity_id)] ??
            String(target.content.target_entity_id)}
        </p>
      )}
      <TechnicalDetails>
        <pre>{JSON.stringify(target.content, null, 2)}</pre>
      </TechnicalDetails>
      <h3>支持与反对依据</h3>
      {!target.evidence.length && (
        <p>没有逐条证据；不能据此宣称内容有原文支持。</p>
      )}
      {target.evidence.map((e) => (
        <article className="list-row" key={e.id}>
          <strong>
            {{ SUPPORTS: "支持", OPPOSES: "反对", CONTEXT: "背景" }[e.stance] ??
              e.stance}{" "}
            · {e.filename}
          </strong>
          <StatusPill value={e.anchor_status} />
          <button
            type="button"
            onClick={() => void open(e.source_version_id, e.source_anchor_id)}
          >
            核对原文定位
          </button>
          <TechnicalDetails>
            <pre>{JSON.stringify(e.locators, null, 2)}</pre>
            <code>{e.excerpt_hash}</code>
          </TechnicalDetails>
        </article>
      ))}
      {loading && <p role="status">正在重新授权并读取原文…</p>}
      {error && <ErrorState message={error} />}
      {preview && (
        <section className="data-card" aria-label="原文核对结果">
          <h3>原文与定位结果</h3>
          <StatusPill value={preview.anchor_status ?? "NO_ANCHOR"} />
          {preview.locator_results.map((r, i) => (
            <p key={i}>
              {r.matched ? "命中" : "未命中"} · {r.safe_detail}
            </p>
          ))}
          <pre className="sanitized-preview">{preview.sanitized_content}</pre>
          <button type="button" onClick={() => setPreview(null)}>
            关闭原文
          </button>
        </section>
      )}
    </section>
  );
}
