import { useEffect, useRef, useState } from "react";
import { ApiError, messageOf, type NexweaveApi } from "./api";
import type { SchemaVersion, SourceDocument, SourceVersion } from "./types";
import type {
  BindingEntity,
  BindingInput,
  BindingValidation,
  CsvBindingPreview,
  SignalBinding,
  TemporalSchema,
} from "./livingTypes";

function bindingError(error: unknown): string {
  const messages: Record<string, string> = {
    DATA_QUALITY_INSUFFICIENT:
      "数据未通过检查：请核对时间是否带时区、采样间隔是否一致、是否至少有 32 行，以及测点是否为有限数值；配置质量列时所有记录必须为 GOOD。",
    UNIT_OR_TYPE_MISMATCH:
      "原始单位或对象类型与已发布模型不一致。请确认源数据单位；系统不会自动换算。",
    BINDING_AMBIGUOUS:
      "每个信号必须使用不同的数值列，且不能与时间列或质量列重复。",
    BINDING_INPUT_UNAVAILABLE:
      "请选择同一空间内的已发布模型、该版本下的对象，以及已解析的 CSV。",
    SOURCE_VERSION_INVALIDATED:
      "该资料版本已失效，不能用于绑定或新预测。请在资料中心选择有效版本。",
    SOURCE_UNAVAILABLE:
      "资料尚未完成解析、未通过扫描或已失效。请在资料中心检查。",
    SOURCE_TYPE_UNSUPPORTED: "请选择不超过 2 MB 的 UTF-8 CSV。",
  };
  return error instanceof ApiError && error.code && messages[error.code]
    ? messages[error.code]
    : messageOf(error);
}

export function BindingWizard({
  api,
  spaceId,
  onCreated,
  onClose,
  onNavigate,
}: {
  api: NexweaveApi;
  spaceId: string;
  onCreated: (binding: SignalBinding, validation: BindingValidation) => void;
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [entities, setEntities] = useState<BindingEntity[]>([]);
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [versions, setVersions] = useState<SourceVersion[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [sourceVersion, setSourceVersion] = useState("");
  const [schemaId, setSchemaId] = useState("");
  const [entityId, setEntityId] = useState("");
  const [profileKey, setProfileKey] = useState("");
  const [preview, setPreview] = useState<CsvBindingPreview | null>(null);
  const [name, setName] = useState("");
  const [timeColumn, setTimeColumn] = useState("");
  const [qualityColumn, setQualityColumn] = useState("");
  const [columns, setColumns] = useState<
    Record<string, { column: string; unit: string }>
  >({});
  const [kind, setKind] = useState<BindingInput["data_kind"]>(
    "IMPORTED_UNVERIFIED",
  );
  const [context, setContext] = useState("");
  const [checked, setChecked] = useState<{
    body: string;
    value: BindingValidation;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const pending = useRef<{ body: string; key: string } | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const schema = schemas.find((s) => s.id === schemaId);
  const temporal = schema?.normalized_snapshot as unknown as
    | TemporalSchema
    | undefined;
  const profile = temporal?.forecastProfiles.find((p) => p.key === profileKey);
  const keys = profile
    ? [profile.target, ...profile.pastCovariates, ...profile.futureCovariates]
    : [];
  const compatible = entities.filter(
    (e) =>
      e.schema_version_id === schemaId &&
      temporal?.signalDefinitions.find((s) => s.key === profile?.target)
        ?.typeKey === e.type_key,
  );
  const body: BindingInput = {
    name: name.trim(),
    entity_id: entityId,
    schema_version_id: schemaId,
    source_version_id: sourceVersion,
    profile_key: profileKey,
    timestamp_column: timeColumn,
    quality_column: qualityColumn || null,
    data_kind: kind,
    operating_context: context.trim(),
    columns: keys.map((key) => ({
      signal_key: key,
      column: columns[key]?.column ?? "",
      unit: columns[key]?.unit ?? "",
    })),
  };
  const signature = JSON.stringify(body);
  const valid = checked?.body === signature ? checked.value : null;
  const complete = Boolean(
    name.trim() &&
      context.trim() &&
      preview &&
      entityId &&
      profile &&
      timeColumn &&
      keys.every((k) => columns[k]?.column && columns[k]?.unit),
  );
  useEffect(() => {
    closeButtonRef.current?.focus();
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api.schemas(spaceId),
      api.bindingEntities(spaceId),
      api.sources(spaceId, { type: "text/csv", limit: 100 }),
    ])
      .then(([s, e, d]) => {
        if (active) {
          setSchemas(
            s.items.filter(
              (v) =>
                v.status === "PUBLISHED" &&
                Array.isArray(v.normalized_snapshot.forecastProfiles) &&
                v.normalized_snapshot.forecastProfiles.length > 0,
            ),
          );
          setEntities(e.items);
          setSources(d.items);
          setCursor(d.next_cursor ?? null);
        }
      })
      .catch((e) => {
        if (active) setError(bindingError(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [api, spaceId, reload]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);
  useEffect(() => {
    let active = true;
    setVersions([]);
    setSourceVersion("");
    setPreview(null);
    if (sourceId)
      api
        .source(sourceId)
        .then((d) => {
          if (active)
            setVersions(
              d.versions.filter(
                (v) =>
                  v.content_type === "text/csv" &&
                  v.status === "PARSED" &&
                  v.size <= 2_000_000,
              ),
            );
        })
        .catch((e) => {
          if (active) setError(bindingError(e));
        });
    return () => {
      active = false;
    };
  }, [api, sourceId, reload]);
  useEffect(() => {
    let active = true;
    setPreview(null);
    setTimeColumn("");
    setQualityColumn("");
    setColumns({});
    setChecked(null);
    if (sourceVersion)
      api
        .csvBindingPreview(spaceId, sourceVersion)
        .then((p) => {
          if (active) setPreview(p);
        })
        .catch((e) => {
          if (active) setError(bindingError(e));
        });
    return () => {
      active = false;
    };
  }, [api, spaceId, sourceVersion, reload]);
  async function validateOrSave(save: boolean) {
    setBusy(true);
    setError("");
    try {
      if (!save) {
        setChecked({
          body: signature,
          value: await api.validateBinding(spaceId, body),
        });
        return;
      }
      if (!valid) return;
      if (pending.current?.body !== signature)
        pending.current = { body: signature, key: crypto.randomUUID() };
      const binding = await api.createBinding(
        spaceId,
        body,
        pending.current.key,
      );
      onCreated(binding, valid);
    } catch (e) {
      setError(bindingError(e));
    } finally {
      setBusy(false);
    }
  }
  async function moreSources() {
    if (!cursor) return;
    setBusy(true);
    try {
      const page = await api.sources(spaceId, {
        type: "text/csv",
        limit: 100,
        cursor,
      });
      setSources((old) => [...old, ...page.items]);
      setCursor(page.next_cursor ?? null);
    } catch (e) {
      setError(bindingError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="living-card binding-wizard"
      role="dialog"
      aria-modal="true"
      aria-labelledby="binding-wizard-title"
      onMouseDown={(event) => event.stopPropagation()}
    >
      <header className="binding-wizard-heading">
        <div>
          <span className="living-kicker">NEW BINDING · FROZEN INPUT</span>
          <h2 id="binding-wizard-title">新增运行数据绑定</h2>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          className="living-quiet-button"
          onClick={onClose}
        >
          关闭
        </button>
      </header>
      <p>
        选择已有资料与知识对象。预检只检查历史数据，不运行模型；保存后绑定不可修改，调整需另建绑定。
      </p>
      {error && (
        <p role="alert" className="living-error">
          {error}{" "}
          <button type="button" onClick={() => setReload((v) => v + 1)}>
            重新加载资源
          </button>
        </p>
      )}
      {loading ? (
        <p role="status">正在读取可用资源…</p>
      ) : (
        <>
          {!schemas.length && (
            <p>
              尚无已发布的时序模型。请先在 Schema Studio 配置并按现有流程发布。
              <button type="button" onClick={() => onNavigate("schemas")}>
                打开 Schema Studio
              </button>
            </p>
          )}
          <fieldset disabled={busy}>
            <legend>1 · 选择数据与知识对象</legend>
            <div className="living-grid">
              <label>
                CSV 资料
                <select
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                >
                  <option value="">选择资料</option>
                  {sources.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                已解析的资料版本
                <select
                  value={sourceVersion}
                  onChange={(e) => setSourceVersion(e.target.value)}
                >
                  <option value="">选择版本</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.filename} · {new Date(v.created_at).toLocaleString()}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                已发布时序模型
                <select
                  value={schemaId}
                  onChange={(e) => {
                    setSchemaId(e.target.value);
                    setProfileKey("");
                    setEntityId("");
                    setColumns({});
                  }}
                >
                  <option value="">选择模型版本</option>
                  {schemas.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.schema_key} · {s.semantic_version}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                预测配置
                <select
                  value={profileKey}
                  onChange={(e) => {
                    setProfileKey(e.target.value);
                    setEntityId("");
                    setColumns({});
                  }}
                >
                  <option value="">选择配置</option>
                  {temporal?.forecastProfiles.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.displayName}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                知识对象
                <select
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                >
                  <option value="">选择对象</option>
                  {compatible.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.display_name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {profile && !compatible.length && (
              <p>
                此版本下没有可绑定的同类型对象。请先通过现有编译流程生成对象。
                <button type="button" onClick={() => onNavigate("compile")}>
                  打开编译中心
                </button>
              </p>
            )}
            {sourceId && !versions.length && (
              <p>
                未找到可用 CSV 版本。请确认文件小于 2 MB，且已经完成解析与扫描。
              </p>
            )}
            <button type="button" onClick={() => onNavigate("sources")}>
              前往资料中心上传 CSV
            </button>
            {cursor && (
              <button type="button" onClick={() => void moreSources()}>
                加载更多资料
              </button>
            )}
            {preview && (
              <>
                <p>
                  共 {preview.row_count} 行 · 下方仅显示前 5 行，单元格最多 128
                  字符。预览不代表观测已核实。
                </p>
                <div className="binding-preview">
                  <table>
                    <thead>
                      <tr>
                        {preview.columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample_rows.map((r, i) => (
                        <tr key={i}>
                          {preview.columns.map((c) => (
                            <td key={c}>{r[c]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h3>2 · 配置列与原始单位</h3>
                <label>
                  时间列
                  <select
                    value={timeColumn}
                    onChange={(e) => setTimeColumn(e.target.value)}
                  >
                    <option value="">选择时间列</option>
                    {preview.columns.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label>
                  质量列（选填）
                  <select
                    value={qualityColumn}
                    onChange={(e) => setQualityColumn(e.target.value)}
                  >
                    <option value="">无质量列</option>
                    {preview.columns.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <p>
                  时间必须包含时区，采样间隔为{" "}
                  {profile?.frequencySeconds ?? "—"}{" "}
                  秒。配置质量列时，每条历史记录质量必须为 GOOD（良好）。
                </p>
                {keys.map((key) => {
                  const signal = temporal!.signalDefinitions.find(
                    (s) => s.key === key,
                  )!;
                  return (
                    <div className="living-path" key={key}>
                      <strong>
                        {signal.displayName} ·{" "}
                        {key === profile?.target
                          ? "预测目标"
                          : profile?.futureCovariates.includes(key)
                            ? "已知未来协变量（需显式假设）"
                            : "历史协变量"}
                      </strong>
                      <label>
                        {signal.displayName}的数据列
                        <select
                          value={columns[key]?.column ?? ""}
                          onChange={(e) =>
                            setColumns((old) => ({
                              ...old,
                              [key]: {
                                unit: old[key]?.unit ?? "",
                                column: e.target.value,
                              },
                            }))
                          }
                        >
                          <option value="">选择数据列</option>
                          {preview.columns.map((c) => (
                            <option key={c}>{c}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        {signal.displayName}的原始单位
                        <input
                          value={columns[key]?.unit ?? ""}
                          placeholder={`模型要求 ${signal.unit}`}
                          onChange={(e) =>
                            setColumns((old) => ({
                              ...old,
                              [key]: {
                                column: old[key]?.column ?? "",
                                unit: e.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                    </div>
                  );
                })}
                <p>请根据测点字典确认原始单位。填入模型单位并不会转换数据。</p>
              </>
            )}
            <h3>3 · 来源说明与验证</h3>
            <label>
              绑定名称
              <input
                maxLength={255}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              数据性质
              <select
                value={kind}
                onChange={(e) =>
                  setKind(e.target.value as BindingInput["data_kind"])
                }
              >
                <option value="IMPORTED_UNVERIFIED">导入数据 · 未经核实</option>
                <option value="SYNTHETIC">合成数据 · 非现场观测</option>
              </select>
            </label>
            <label>
              运行工况说明
              <textarea
                maxLength={1000}
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="说明设备运行条件、数据来源及尚未确认事项"
              />
            </label>
            {valid && (
              <p role="status">
                预检通过：最近 {valid.point_count} 个记录点，
                {new Date(valid.start).toLocaleString()} 至{" "}
                {new Date(valid.end).toLocaleString()}。更改配置后需重新预检。
              </p>
            )}
            <button
              type="button"
              disabled={!complete}
              onClick={() => void validateOrSave(false)}
            >
              {busy ? "正在处理…" : "验证绑定与数据"}
            </button>
            <button
              type="button"
              disabled={!valid}
              onClick={() => void validateOrSave(true)}
            >
              保存绑定
            </button>
          </fieldset>
        </>
      )}
      <button type="button" disabled={busy} onClick={onClose}>
        关闭绑定配置
      </button>
    </section>
  );
}
