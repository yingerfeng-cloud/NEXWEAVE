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
import type { Claim } from "./types";

export function ClaimCenter(props: { api: NexweaveApi; spaceId: string }) {
  return <ClaimView key={props.spaceId} {...props} />;
}

function ClaimView({ api, spaceId }: { api: NexweaveApi; spaceId: string }) {
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

export { ConflictCenter, ReviewCenter } from "./ReviewOperations";
