import { useEffect, useState } from "react";
import { messageOf, type NexweaveApi } from "./api";
import type { ForecastArtifact, ForecastRun } from "./livingTypes";

import { compatibleForecasts } from "./livingComparison";

export function ForecastComparison({
  api,
  artifact,
  runs,
  bindingId,
}: {
  api: NexweaveApi;
  artifact: ForecastArtifact;
  runs: ForecastRun[];
  bindingId: string;
}) {
  const [id, setId] = useState("");
  const [other, setOther] = useState<ForecastArtifact | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setOther(null);
    setError("");
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api
      .forecastArtifact(id)
      .then((a) => {
        if (active) setOther(a);
      })
      .catch((e) => {
        if (active) setError(messageOf(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api, id]);
  const options = runs.filter(
    (r) =>
      r.request.binding_id === bindingId &&
      r.status === "SUCCEEDED" &&
      r.artifact_id !== artifact.id,
  );
  const compatible =
    other &&
    options.some((r) => r.artifact_id === other.id) &&
    compatibleForecasts(artifact, other);
  return (
    <section
      className="living-card living-compare-card"
      aria-label="同窗口场景比较"
    >
      <div className="living-card-heading">
        <div>
          <span className="living-kicker">CONDITION DIFF · READ ONLY</span>
          <h2>同窗口场景比较</h2>
        </div>
        <span className="living-tag">不改变任何历史制品</span>
      </div>
      <div className="living-compare-current">
        <span>
          <small>当前场景</small>
          <strong>{artifact.content.context.scenario_name}</strong>
        </span>
        <span>
          <small>模型</small>
          <strong>{artifact.content.result.model_revision}</strong>
        </span>
        <span>
          <small>预测末端</small>
          <strong>
            {new Date(
              artifact.content.context.prediction_timestamps.at(-1)!,
            ).toLocaleString()}
          </strong>
        </span>
      </div>
      <label className="living-compare-select">
        <span>
          选择对照预测 <em>同一绑定 · 已完成</em>
        </span>
        <select
          value={id}
          onChange={(e) => {
            setId(e.target.value);
            setError("");
          }}
          disabled={loading}
        >
          <option value="">选择同一绑定的成功记录</option>
          {options.map((r) => (
            <option key={r.id} value={r.artifact_id!}>
              {r.request.scenario_name} ·{" "}
              {new Date(r.created_at).toLocaleString()}
            </option>
          ))}
        </select>
      </label>
      {!options.length && (
        <p>请在相同绑定与历史窗口下再运行一个场景，完成后即可比较。</p>
      )}
      {error && (
        <p className="living-field-error" role="alert">
          {error}
        </p>
      )}
      {id && loading && (
        <p className="living-inline-status" role="status">
          正在读取对照制品…
        </p>
      )}
      {other && !compatible && (
        <p role="status">
          两个结果的历史窗口、模型或时间轴不一致，不能作为同窗口场景差异比较。
        </p>
      )}
      {other && compatible && (
        <>
          <div className="living-compare-result" aria-live="polite">
            <table>
              <thead>
                <tr>
                  <th>末端分位值（{artifact.content.context.unit}）</th>
                  <th>当前场景</th>
                  <th>对照场景</th>
                  <th>当前 − 对照</th>
                </tr>
              </thead>
              <tbody>
                {["0.1", "0.5", "0.9"].map((q) => {
                  const a = artifact.content.result.quantiles[q]?.at(-1),
                    b = other.content.result.quantiles[q]?.at(-1);
                  return (
                    <tr key={q}>
                      <td>P{Number(q) * 100}</td>
                      <td>{a?.toFixed(3) ?? "未提供"}</td>
                      <td>{b?.toFixed(3) ?? "未提供"}</td>
                      <td>
                        {a !== undefined && b !== undefined
                          ? (a - b).toFixed(3)
                          : "不可比较"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p>
              历史窗口逐点相同；差值为条件预测比较，不是因果效应，分位差也不是差值的概率区间。
            </p>
          </div>
        </>
      )}
    </section>
  );
}
