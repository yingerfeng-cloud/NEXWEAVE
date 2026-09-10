import { useEffect, useRef, useState } from "react";
import { messageOf, type NexweaveApi } from "./api";
import type {
  ForecastArtifact,
  ForecastRequest,
  ForecastRuntime,
  ForecastRun,
  SignalBinding,
} from "./livingTypes";
import { forecastProviderLabel, forecastStatusLabel } from "./livingTypes";
import { BindingWizard } from "./BindingWizard";
import { ForecastComparison } from "./ForecastComparison";
import { ForecastKnowledge } from "./ForecastKnowledge";
import "./living.css";

export function ForecastChart({ artifact }: { artifact: ForecastArtifact }) {
  const [historyWindow, setHistoryWindow] = useState(120);
  const { context, result } = artifact.content;
  const observations = context.observations.slice(-historyWindow);
  const history = observations.map((p) => p.values[context.target]);
  const q = result.quantiles;
  const lower = q["0.1"] ?? [];
  const median = q["0.5"] ?? [];
  const upper = q["0.9"] ?? [];
  const all = [...history, ...lower, ...median, ...upper].filter((n) =>
    Number.isFinite(n),
  );
  const rangeMin = all.length ? Math.min(...all) : 0;
  const rangeMax = all.length ? Math.max(...all) : 1;
  const padding = Math.max(0.5, (rangeMax - rangeMin) * 0.08);
  const min = rangeMin - padding;
  const max = rangeMax + padding;
  const count = history.length + median.length;
  const x = (i: number) => 56 + (i / Math.max(1, count - 1)) * 820;
  const y = (n: number) => 244 - ((n - min) / (max - min)) * 208;
  const line = (a: number[], start: number) =>
    a.map((v, i) => `${x(start + i)},${y(v)}`).join(" ");
  const lastObserved = history.at(-1);
  const lastP50 = median.at(-1);
  const peakP90 = upper.length ? Math.max(...upper) : undefined;
  return (
    <figure className="living-chart">
      <div className="living-chart-heading">
        <div>
          <span className="living-kicker">
            FORECAST ARTIFACT ·{" "}
            {forecastProviderLabel[result.provider_id] ?? result.provider_id}
          </span>
          <figcaption>历史窗口与条件预测 · {context.unit}</figcaption>
        </div>
        <div
          className="living-chart-controls"
          role="group"
          aria-label="历史窗口"
        >
          {[24, 120].map((size) => (
            <button
              type="button"
              key={size}
              aria-pressed={historyWindow === size}
              onClick={() => setHistoryWindow(size)}
            >
              最近 {Math.min(size, context.observations.length)} 点
            </button>
          ))}
        </div>
      </div>
      <div className="living-chart-legend" aria-label="图例">
        <span>
          <i className="legend-line observed" />
          输入记录
        </span>
        <span>
          <i className="legend-line forecast" />
          P50 预测
        </span>
        <span>
          <i className="legend-band" />
          P10–P90 区间
        </span>
      </div>
      <div className="living-chart-summary">
        <span>
          <small>输入截止</small>
          <strong>{new Date(context.origin).toLocaleString()}</strong>
        </span>
        <span>
          <small>P50 末端</small>
          <strong>
            {lastP50 === undefined
              ? "—"
              : `${lastP50.toFixed(2)} ${context.unit}`}
          </strong>
        </span>
        <span>
          <small>P90 峰值</small>
          <strong>
            {peakP90 === undefined
              ? "—"
              : `${peakP90.toFixed(2)} ${context.unit}`}
          </strong>
        </span>
      </div>
      <svg
        viewBox="0 0 920 290"
        role="img"
        aria-label="历史输入和概率预测区间图"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line
              x1="56"
              x2="876"
              y1={244 - t * 208}
              y2={244 - t * 208}
              stroke="currentColor"
              opacity=".12"
            />
            <text x="4" y={249 - t * 208} fill="currentColor" fontSize="12">
              {(min + t * (max - min)).toFixed(1)}
            </text>
          </g>
        ))}
        {lower.length && upper.length ? (
          <polygon
            points={`${line(lower, history.length)} ${upper
              .map((v, i) => `${x(history.length + i)},${y(v)}`)
              .reverse()
              .join(" ")}`}
            fill="#9878ff"
            opacity=".23"
          />
        ) : null}
        <polyline
          points={line(history, 0)}
          fill="none"
          stroke="#36d6d9"
          strokeWidth="2.3"
        />
        {lastObserved !== undefined && (
          <circle
            cx={x(history.length - 1)}
            cy={y(lastObserved)}
            r="4"
            fill="var(--nw-cyan)"
          >
            <title>
              输入截止：{lastObserved.toFixed(2)} {context.unit}
            </title>
          </circle>
        )}
        {lastP50 !== undefined && (
          <circle
            cx={x(count - 1)}
            cy={y(lastP50)}
            r="4"
            fill="var(--nw-violet-highlight)"
          >
            <title>
              预测末端 P50：{lastP50.toFixed(2)} {context.unit}
            </title>
          </circle>
        )}
        <polyline
          points={line(median, history.length)}
          fill="none"
          stroke="#b899ff"
          strokeWidth="2.3"
        />
        <line
          x1={x(history.length - 1)}
          x2={x(history.length - 1)}
          y1="30"
          y2="244"
          stroke="#b8b4ce"
          strokeDasharray="4 4"
        />
        <text x="56" y="275" fill="currentColor" fontSize="12">
          {new Date(
            observations[0]?.timestamp ?? context.origin,
          ).toLocaleString()}
        </text>
        <text
          x="876"
          y="275"
          textAnchor="end"
          fill="currentColor"
          fontSize="12"
        >
          {new Date(context.prediction_timestamps.at(-1)!).toLocaleString()}
        </text>
      </svg>
      <p>
        当前为 {history.length} 个历史点 + {median.length}{" "}
        个未来点。历史回放可获得性未经核实；区间未经工业数据校准。
      </p>
    </figure>
  );
}

export function LivingKnowledge({
  api,
  spaceId,
  view,
  onNavigate,
}: {
  api: NexweaveApi;
  spaceId: string;
  view: string;
  onNavigate: (path: string) => void;
}) {
  const [showBinding, setShowBinding] = useState(false);
  const [defaults, setDefaults] = useState<
    Record<string, Record<string, number>>
  >({});
  const [historyPoints, setHistoryPoints] = useState(720);
  const [bindings, setBindings] = useState<SignalBinding[]>([]);
  const [bindingId, setBindingId] = useState("");
  const [runs, setRuns] = useState<ForecastRun[]>([]);
  const [selected, setSelected] = useState("");
  const [artifact, setArtifact] = useState<ForecastArtifact | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runtime, setRuntime] = useState<ForecastRuntime | null>(null);
  const [runtimeError, setRuntimeError] = useState(false);
  const [runtimeReload, setRuntimeReload] = useState(0);
  const [resourceLoading, setResourceLoading] = useState(true);
  const [resourceReload, setResourceReload] = useState(0);
  const pending = useRef<{ body: string; key: string } | null>(null);
  const commandKeys = useRef(new Map<string, string>());
  useEffect(() => {
    let active = true;
    setRuntime(null);
    setRuntimeError(false);
    if (!spaceId) {
      setResourceLoading(false);
      return;
    }
    const refresh = () =>
      api
        .forecastRuntime(spaceId)
        .then((value) => {
          if (active) {
            setRuntime(value);
            setRuntimeError(false);
          }
        })
        .catch(() => {
          if (active) setRuntimeError(true);
        });
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [api, spaceId, runtimeReload]);
  async function command(action: "cancel" | "retry") {
    if (!run) return;
    setBusy(true);
    setError("");
    const operation = `${run.id}/${action}`;
    const key = commandKeys.current.get(operation) ?? crypto.randomUUID();
    commandKeys.current.set(operation, key);
    try {
      const result = await api.forecastCommand(
        run.id,
        action,
        action === "cancel" ? "用户取消本次预测" : "用户以冻结输入重新运行",
        key,
      );
      setRuns((old) => [result, ...old.filter((r) => r.id !== result.id)]);
      setSelected(result.id);
      commandKeys.current.delete(operation);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  const [paths, setPaths] = useState<
    Record<string, { start: number; end: number }>
  >({});
  const [threshold, setThreshold] = useState("");
  const [horizon, setHorizon] = useState(120);
  const [pages, setPages] = useState<
    { id: string; title: string; primary_entity_id: string | null }[]
  >([]);
  const binding = bindings.find((b) => b.id === bindingId);
  const run = runs.find((r) => r.id === selected);
  const activeRunId = run?.id;
  const activeRunStatus = run?.status;
  const target = binding?.snapshot.signals.find(
    (signal) => signal.key === binding.snapshot.profile.target,
  );
  const maxHorizon = binding?.snapshot.profile.maxHorizon ?? 120;
  const invalidHistory =
    !Number.isInteger(historyPoints) ||
    historyPoints < 32 ||
    historyPoints > 8192;
  const invalidHorizon =
    !Number.isInteger(horizon) || horizon < 1 || horizon > maxHorizon;
  const invalidThreshold =
    threshold.trim() !== "" && !Number.isFinite(Number(threshold));
  const missingFuturePath = Boolean(
    binding?.snapshot.profile.futureCovariates.some(
      (key) =>
        !Number.isFinite(paths[key]?.start) ||
        !Number.isFinite(paths[key]?.end),
    ),
  );
  const runInProgress = Boolean(
    run && ["QUEUED", "RUNNING"].includes(run.status),
  );
  useEffect(() => {
    let active = true;
    setResourceLoading(true);
    setBindings([]);
    setBindingId("");
    setRuns([]);
    setSelected("");
    setPages([]);
    setError("");
    if (!spaceId) return;
    Promise.all([
      api.signalBindings(spaceId),
      api.forecastRuns(spaceId),
      api.wikiPages(spaceId),
    ])
      .then(([b, r, p]) => {
        if (active) {
          setBindings(b.items);
          setBindingId(b.items[0]?.id ?? "");
          setRuns(r.items);
          setSelected(
            r.items.find((item) => item.request.binding_id === b.items[0]?.id)
              ?.id ?? "",
          );
          setPages(p.items);
        }
      })
      .catch((e) => {
        if (active) setError(messageOf(e));
      })
      .finally(() => {
        if (active) setResourceLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api, spaceId, resourceReload]);
  useEffect(() => {
    let active = true;
    setArtifact(null);
    if (run?.artifact_id)
      api
        .forecastArtifact(run.artifact_id)
        .then((a) => {
          if (active) setArtifact(a);
        })
        .catch((e) => {
          if (active) setError(messageOf(e));
        });
    return () => {
      active = false;
    };
  }, [api, run?.artifact_id]);
  useEffect(() => {
    let active = true;
    if (!activeRunId || !["QUEUED", "RUNNING"].includes(activeRunStatus ?? ""))
      return;
    const timer = window.setInterval(() => {
      api
        .forecastRun(activeRunId)
        .then((r) => {
          if (active) setRuns((old) => old.map((v) => (v.id === r.id ? r : v)));
        })
        .catch((e) => {
          if (active) setError(messageOf(e));
        });
    }, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [api, activeRunId, activeRunStatus]);
  useEffect(() => {
    if (!binding) return;
    const values =
      artifact?.content.context.observations.at(-1)?.values ??
      defaults[binding.id];
    setPaths(
      Object.fromEntries(
        binding.snapshot.profile.futureCovariates.map((k) => [
          k,
          {
            start: values?.[k] ?? NaN,
            end:
              run?.request.future_paths
                .find((p) => p.signal_key === k)
                ?.values.at(-1) ??
              values?.[k] ??
              NaN,
          },
        ]),
      ),
    );
    setHorizon(
      run?.request.horizon ??
        Math.min(120, binding.snapshot.profile.maxHorizon),
    );
    setThreshold(
      run?.request.event_rule ? String(run.request.event_rule.threshold) : "",
    );
    setHistoryPoints(run?.request.history_points ?? 720);
  }, [binding, artifact, run, defaults]);
  async function submit() {
    if (
      !binding ||
      busy ||
      runInProgress ||
      invalidHistory ||
      invalidHorizon ||
      invalidThreshold ||
      missingFuturePath
    )
      return;
    setBusy(true);
    setError("");
    try {
      const future_paths = binding.snapshot.profile.futureCovariates.map(
        (key) => {
          const v = paths[key];
          if (!v || !Number.isFinite(v.start) || !Number.isFinite(v.end))
            throw new Error("请输入完整的未来路径。");
          return {
            signal_key: key,
            unit: binding.snapshot.signals.find((s) => s.key === key)!.unit,
            values: Array.from(
              { length: horizon },
              (_, i) => v.start + ((v.end - v.start) * (i + 1)) / horizon,
            ),
          };
        },
      );
      const name =
        future_paths
          .map(
            (p) =>
              `${binding.snapshot.signals.find((s) => s.key === p.signal_key)!.displayName} ${paths[p.signal_key].start}→${paths[p.signal_key].end}${p.unit}`,
          )
          .join("；") || "历史条件延续";
      const target = binding.snapshot.signals.find(
        (s) => s.key === binding.snapshot.profile.target,
      )!;
      const body: ForecastRequest = {
        binding_id: binding.id,
        provider_id: "chronos2",
        horizon,
        history_points: historyPoints,
        scenario_name: name.slice(0, 128),
        future_paths,
        ...(threshold !== ""
          ? {
              event_rule: {
                threshold: Number(threshold),
                unit: target.unit,
                label: `${target.displayName}进入关注区间`,
                authority: "USER_DEFINED_UNVERIFIED" as const,
              },
            }
          : {}),
      };
      const signature = JSON.stringify({ spaceId, body });
      if (pending.current?.body !== signature)
        pending.current = { body: signature, key: crypto.randomUUID() };
      const r = await api.createForecast(spaceId, body, pending.current.key);
      pending.current = null;
      setRuns((old) => [r, ...old.filter((item) => item.id !== r.id)]);
      setSelected(r.id);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  function resetScenario() {
    if (!binding) return;
    const values =
      artifact?.content.context.observations.at(-1)?.values ??
      defaults[binding.id] ??
      {};
    setPaths(
      Object.fromEntries(
        binding.snapshot.profile.futureCovariates.map((key) => [
          key,
          { start: values[key] ?? NaN, end: values[key] ?? NaN },
        ]),
      ),
    );
    setThreshold("");
    setHorizon(Math.min(120, maxHorizon));
    setHistoryPoints(720);
  }
  const related = pages.filter(
    (p) => p.primary_entity_id === binding?.entity_id,
  );
  return (
    <section className="living-workspace">
      <header className="living-header">
        <div>
          <p className="living-kicker">LIVING KNOWLEDGE · M9.5</p>
          <h1>
            {view === "ask"
              ? "在未来工况下，对象可能怎样变化"
              : view === "graph"
                ? "运行知识关系"
                : view === "schemas"
                  ? "时序语义与信号角色"
                  : view === "integrations"
                    ? "运行数据绑定"
                    : "对象的运行与未来"}
          </h1>
          <p>基于有来源的运行窗口和显式未来输入，生成可追溯的条件预测。</p>
        </div>
        <div className="living-header-actions">
          <span className="living-engine-badge">
            <i /> Chronos-2 · 时序推理
          </span>
          <button
            className="primary"
            type="button"
            onClick={() => setShowBinding(true)}
          >
            + 新增数据绑定
          </button>
        </div>
      </header>
      <div
        role="status"
        aria-live="polite"
        className={`living-runtime ${runtimeError ? "is-error" : runtime?.worker_status === "AVAILABLE" ? "is-online" : "is-offline"}`}
      >
        <div className="living-runtime-main">
          <i aria-hidden="true" />
          <div>
            <strong>时序预测服务</strong>
            <span>
              {runtimeError
                ? "无法确认状态"
                : runtime?.worker_status === "AVAILABLE"
                  ? "在线，可提交新任务"
                  : runtime
                    ? "预测服务离线；任务记录仍会保留"
                    : "正在检查服务…"}
            </span>
          </div>
        </div>
        <div className="living-runtime-stats">
          <span>
            <small>等待</small>
            <strong>{runtime && !runtimeError ? runtime.queued : "—"}</strong>
          </span>
          <span>
            <small>运行</small>
            <strong>{runtime && !runtimeError ? runtime.running : "—"}</strong>
          </span>
          <span>
            <small>待投递</small>
            <strong>
              {runtime && !runtimeError ? runtime.delivery_pending : "—"}
            </strong>
          </span>
          <span>
            <small>Worker</small>
            <strong>
              {runtime && !runtimeError ? runtime.worker_count : "—"}
            </strong>
          </span>
          <span>
            <small>版本</small>
            <strong>
              {runtime && !runtimeError ? runtime.implementation_version : "—"}
            </strong>
          </span>
        </div>
        <button
          className="living-quiet-button"
          type="button"
          onClick={() => setRuntimeReload((value) => value + 1)}
        >
          刷新状态
        </button>
      </div>
      {error && (
        <p role="alert" className="living-error">
          {error}
          <button
            type="button"
            onClick={() => setResourceReload((value) => value + 1)}
          >
            重新加载
          </button>
        </p>
      )}
      {showBinding && (
        <div
          className="binding-wizard-layer"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowBinding(false);
          }}
        >
          <BindingWizard
            key={spaceId}
            api={api}
            spaceId={spaceId}
            onNavigate={onNavigate}
            onClose={() => setShowBinding(false)}
            onCreated={(b, validation) => {
              setBindings((old) => [
                b,
                ...old.filter((item) => item.id !== b.id),
              ]);
              setBindingId(b.id);
              setSelected("");
              setArtifact(null);
              setDefaults((old) => ({
                ...old,
                [b.id]: validation.latest_values,
              }));
              setShowBinding(false);
            }}
          />
        </div>
      )}
      {resourceLoading ? (
        <div className="living-card living-loading" role="status">
          <i />
          正在读取绑定、预测记录和关联知识…
        </div>
      ) : !bindings.length ? (
        <div className="living-card living-empty-binding">
          <div className="living-empty-icon">◈</div>
          <div>
            <span className="living-kicker">STEP 01 · DATA FOUNDATION</span>
            <h2>尚未配置运行数据绑定</h2>
            <p>
              先通过资料中心上传受控
              CSV，再选择已发布时序模型和知识对象。绑定保存后不可修改，调整时需另建版本。
            </p>
            <div className="living-empty-actions">
              <button
                className="primary"
                type="button"
                onClick={() => setShowBinding(true)}
              >
                开始配置绑定 →
              </button>
              <button type="button" onClick={() => onNavigate("sources")}>
                打开资料中心
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="living-toolbar">
            <label className="living-binding-select">
              <span>知识对象与数据绑定</span>
              <select
                value={bindingId}
                onChange={(e) => {
                  setBindingId(e.target.value);
                  setSelected(
                    runs.find((r) => r.request.binding_id === e.target.value)
                      ?.id ?? "",
                  );
                  setArtifact(null);
                  setError("");
                }}
              >
                {bindings.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.snapshot.entity.display_name} · {b.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="living-binding-meta">
              <span
                className={`living-tag ${binding?.data_kind === "SYNTHETIC" ? "is-synthetic" : "is-imported"}`}
              >
                {binding?.data_kind === "SYNTHETIC"
                  ? "合成数据 · 非现场观测"
                  : "导入数据 · 未经核实"}
              </span>
              <span className="living-binding-target">
                目标：{target?.displayName ?? "—"} · {target?.unit ?? "—"}
              </span>
            </div>
          </div>
          <div className="living-grid">
            <section className="living-card living-config-card">
              <div className="living-card-heading">
                <div>
                  <span className="living-kicker">STEP 02 · SCENARIO</span>
                  <h2>条件预测场景</h2>
                </div>
                <button
                  type="button"
                  className="living-quiet-button"
                  onClick={resetScenario}
                >
                  恢复最近输入
                </button>
              </div>
              <p className="living-context">{binding?.operating_context}</p>
              <form
                className="living-run-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void submit();
                }}
              >
                <div className="living-section-label">
                  未来路径 <span>显式用户假设</span>
                </div>
                {binding?.snapshot.profile.futureCovariates.map((key) => {
                  const signal = binding.snapshot.signals.find(
                    (s) => s.key === key,
                  )!;
                  return (
                    <div className="living-path" key={key}>
                      <strong>
                        {signal.displayName}（{signal.unit}）
                      </strong>
                      <label>
                        <span>
                          起始值 <em>{signal.unit}</em>
                        </span>
                        <input
                          type="number"
                          inputMode="decimal"
                          step="any"
                          aria-label={`${signal.displayName}起始值`}
                          value={
                            Number.isFinite(paths[key]?.start)
                              ? paths[key].start
                              : ""
                          }
                          onChange={(e) =>
                            setPaths((p) => ({
                              ...p,
                              [key]: {
                                ...p[key],
                                start:
                                  e.target.value === ""
                                    ? NaN
                                    : Number(e.target.value),
                              },
                            }))
                          }
                        />
                      </label>
                      <span>→</span>
                      <label>
                        <span>
                          末端值 <em>{signal.unit}</em>
                        </span>
                        <input
                          type="number"
                          inputMode="decimal"
                          step="any"
                          aria-label={`${signal.displayName}末端值`}
                          value={
                            Number.isFinite(paths[key]?.end)
                              ? paths[key].end
                              : ""
                          }
                          onChange={(e) =>
                            setPaths((p) => ({
                              ...p,
                              [key]: {
                                ...p[key],
                                end:
                                  e.target.value === ""
                                    ? NaN
                                    : Number(e.target.value),
                              },
                            }))
                          }
                        />
                      </label>
                    </div>
                  );
                })}
                <div className="living-section-label">
                  时间范围与规则 <span>可选阈值只用于演示提示</span>
                </div>
                <div className="living-path living-range-fields">
                  <label>
                    <span>
                      历史窗口 <em>步</em>
                    </span>
                    <input
                      type="number"
                      min="32"
                      max="8192"
                      step="1"
                      aria-describedby="forecast-window-help"
                      value={historyPoints}
                      onChange={(e) => setHistoryPoints(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    <span>
                      预测步数 <em>步</em>
                    </span>
                    <input
                      type="number"
                      min="1"
                      max={maxHorizon}
                      step="1"
                      value={horizon}
                      onChange={(e) => setHorizon(Number(e.target.value))}
                    />
                  </label>
                  <label>
                    <span>
                      关注阈值 <em>{target?.unit ?? "单位"} · 选填</em>
                    </span>
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      aria-label="关注阈值"
                      value={threshold}
                      onChange={(e) => setThreshold(e.target.value)}
                      placeholder="未经批准的用户阈值"
                    />
                  </label>
                </div>
                <p id="forecast-window-help" className="living-form-help">
                  每步 {binding?.snapshot.profile.frequencySeconds}{" "}
                  秒；未来输入按线性路径展开。条件预测不等于因果推断。
                </p>
                {(invalidHistory ||
                  invalidHorizon ||
                  invalidThreshold ||
                  missingFuturePath) && (
                  <p className="living-field-error" role="alert">
                    {invalidHistory
                      ? "历史窗口需为 32–8192 的整数。"
                      : invalidHorizon
                        ? `预测步数需为 1–${maxHorizon} 的整数。`
                        : invalidThreshold
                          ? "关注阈值必须是有限数值。"
                          : "请为每个未来协变量填写起始值和末端值。"}
                  </p>
                )}
                <div className="living-form-footer">
                  <span className="living-submit-note">
                    <i />{" "}
                    {runInProgress
                      ? "当前已有预测运行中"
                      : "提交后输入与数据绑定会被冻结"}
                  </span>
                  <button
                    className="primary"
                    type="submit"
                    disabled={
                      busy ||
                      runInProgress ||
                      invalidHistory ||
                      invalidHorizon ||
                      invalidThreshold ||
                      missingFuturePath
                    }
                  >
                    {busy
                      ? "正在提交…"
                      : runInProgress
                        ? "预测运行中"
                        : "运行 Chronos-2 预测 →"}
                  </button>
                </div>
              </form>
            </section>
            <section className="living-card living-runs-card">
              <div className="living-card-heading">
                <div>
                  <span className="living-kicker">STEP 03 · RUN HISTORY</span>
                  <h2>预测记录</h2>
                </div>
                <button
                  type="button"
                  className="living-quiet-button"
                  onClick={() => setResourceReload((value) => value + 1)}
                >
                  刷新列表
                </button>
              </div>
              <label className="living-run-select">
                <span>场景与模型</span>
                <select
                  value={selected}
                  onChange={(e) => {
                    setSelected(e.target.value);
                    setArtifact(null);
                    setError("");
                  }}
                >
                  <option value="">选择一条运行记录</option>
                  {runs
                    .filter((r) => r.request.binding_id === bindingId)
                    .map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.request.scenario_name} ·{" "}
                        {forecastProviderLabel[r.request.provider_id] ??
                          r.request.provider_id}{" "}
                        · {forecastStatusLabel[r.status] ?? r.status}
                      </option>
                    ))}
                </select>
              </label>
              {!runs.filter((item) => item.request.binding_id === bindingId)
                .length && (
                <div className="living-run-empty">
                  <span>◌</span>
                  <p>
                    当前绑定还没有运行记录。调整左侧场景后即可提交第一条
                    Chronos-2 预测。
                  </p>
                </div>
              )}
              {run && (
                <div
                  className={`living-run-status ${run.status.toLowerCase()}`}
                  role="status"
                >
                  <span className="living-status-dot" />
                  <div>
                    <strong>
                      {forecastStatusLabel[run.status] ?? run.status}
                    </strong>
                    <small>
                      {forecastProviderLabel[run.request.provider_id] ??
                        run.request.provider_id}{" "}
                      · {new Date(run.created_at).toLocaleString()}
                    </small>
                  </div>
                  {run.error_code && <code>{run.error_code}</code>}
                </div>
              )}
              {run?.delivery_status === "RETRYING" && (
                <p>投递暂时中断，系统会自动重试，无需重复提交。</p>
              )}
              {run?.retry_of && <p>本次沿用原任务的冻结输入；历史记录保留。</p>}
              {run && ["QUEUED", "RUNNING"].includes(run.status) && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void command("cancel")}
                >
                  取消本次预测
                </button>
              )}
              {run && ["FAILED", "CANCELLED"].includes(run.status) && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void command("retry")}
                >
                  以原输入重新运行
                </button>
              )}
              {run?.status === "CANCELLED" && (
                <p>已停止结果发布。正在执行的计算可能稍后结束。</p>
              )}
              <p className="living-disclaimer">
                数值由模型生成，风险叙述由可检查规则组装；此预览不调用自由文本
                LLM，也不自动诊断。
              </p>
              {related.map((p) => (
                <button
                  type="button"
                  className="living-link"
                  key={p.id}
                  onClick={() =>
                    onNavigate(`wiki?page=${encodeURIComponent(p.id)}`)
                  }
                >
                  关联 Wiki：{p.title}（草稿状态请查看原页）
                </button>
              ))}
            </section>
          </div>
          {(view === "schemas" || view === "integrations") && binding && (
            <section className="living-card">
              <h2>冻结的时序语义</h2>
              <table>
                <thead>
                  <tr>
                    <th>信号</th>
                    <th>角色</th>
                    <th>单位</th>
                  </tr>
                </thead>
                <tbody>
                  {binding.snapshot.signals.map((s) => (
                    <tr key={s.key}>
                      <td>{s.displayName}</td>
                      <td>
                        {s.key === binding.snapshot.profile.target
                          ? "Target"
                          : binding.snapshot.profile.futureCovariates.includes(
                                s.key,
                              )
                            ? "Known Future Covariate（用户假设）"
                            : "Past Covariate"}
                      </td>
                      <td>{s.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>Context：{binding.operating_context}</p>
              <p>当前为版本化 CSV 绑定；外部 Historian 实时连接尚未接入。</p>
            </section>
          )}
          {artifact && (
            <>
              <ForecastChart artifact={artifact} />
              <ForecastComparison
                key={artifact.id}
                api={api}
                artifact={artifact}
                runs={runs}
                bindingId={bindingId}
              />
              {view === "graph" && (
                <div className="living-lineage" aria-label="预测来源关系">
                  <span>对象 / Schema</span>→
                  <span>SourceVersion / Binding</span>→
                  <span>ForecastContext</span>→
                  <span>{artifact.content.result.provider_id}</span>→
                  <span>ForecastArtifact</span>→
                  <span>
                    Potential Event：{artifact.content.potential_events.length}
                  </span>
                </div>
              )}
              <div className="living-grid">
                <section className="living-card">
                  <span className="living-tag">Observed · 输入记录</span>
                  <p>{artifact.content.risk_narrative.observed}</p>
                  <span className="living-tag">Forecast · 模型派生</span>
                  <p>{artifact.content.risk_narrative.forecast}</p>
                  <h2>Potential Event</h2>
                  {artifact.content.potential_events.length ? (
                    artifact.content.potential_events.map((e) => (
                      <div key={e.first_timestamp}>
                        <strong>{e.label}</strong>
                        <p>{e.explanation}</p>
                        <p>
                          首次匹配：
                          {new Date(e.first_timestamp).toLocaleString()}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p>
                      {artifact.content.event_evaluation === "NOT_EVALUATED"
                        ? "未评估阈值条件"
                        : "当前规则未匹配。不能据此断言设备安全。"}
                    </p>
                  )}
                </section>
                <section className="living-card">
                  <span className="living-tag">Hypothesis · 待核实</span>
                  {artifact.content.hypotheses.map((h) => (
                    <div key={h.statement}>
                      <p>{h.statement}</p>
                      <p>{h.verification}</p>
                    </div>
                  ))}
                  <span className="living-tag">
                    Released Knowledge · 独立依据
                  </span>
                  <p>{artifact.content.risk_narrative.knowledge}</p>
                  <p>
                    不会把预测曲线转成 Evidence、Observed Fact 或已发布知识。
                  </p>
                </section>
              </div>
              <ForecastKnowledge
                key={`${spaceId}:${artifact.id}`}
                api={api}
                spaceId={spaceId}
                artifactId={artifact.id}
                onNavigate={onNavigate}
              />
              <details className="living-card">
                <summary>追溯与限制</summary>
                <p>
                  模型：{artifact.content.result.provider_id} ·{" "}
                  {artifact.content.result.model_revision}
                </p>
                <p>产物：{artifact.id}</p>
                <p className="living-hash">{artifact.content_checksum}</p>
                <p>{artifact.content.risk_narrative.limitations.join("；")}</p>
              </details>
            </>
          )}
        </>
      )}
    </section>
  );
}
