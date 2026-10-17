import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  CompileJob,
  GovernanceObject,
  SchemaVersion,
  SourceDocument,
  SourceVersion,
} from "./types";

export function CompileCenter(props: {
  api: NexweaveApi;
  spaceId: string;
  onNavigate?: (path: string) => void;
}) {
  return <CompileCenterView key={props.spaceId} {...props} />;
}

function CompileCenterView({
  api,
  spaceId,
  onNavigate,
}: {
  api: NexweaveApi;
  spaceId: string;
  onNavigate?: (path: string) => void;
}) {
  const [jobs, setJobs] = useState<CompileJob[]>([]);
  const [schemas, setSchemas] = useState<SchemaVersion[]>([]);
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [prompts, setPrompts] = useState<GovernanceObject[]>([]);
  const [models, setModels] = useState<GovernanceObject[]>([]);
  const [schemaId, setSchemaId] = useState("");
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [promptId, setPromptId] = useState("");
  const [modelId, setModelId] = useState("");
  const [mode, setMode] = useState<CompileJob["mode"]>("FULL");
  const [selected, setSelected] = useState<CompileJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sourcesUnavailable, setSourcesUnavailable] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const loadEpoch = useRef(0);
  const hasLoadedRef = useRef(false);

  const versions = useMemo(
    () =>
      sources
        .flatMap((source) => source.versions)
        .filter((version) => ["PARSED", "PARTIAL"].includes(version.status)),
    [sources],
  );

  const load = useCallback(async () => {
    const epoch = ++loadEpoch.current;
    if (!spaceId) {
      setJobs([]);
      setSchemas([]);
      setSources([]);
      setPrompts([]);
      setModels([]);
      setSelected(null);
      setError("");
      setNotice("");
      setSourcesUnavailable(false);
      setLoading(false);
      hasLoadedRef.current = true;
      return;
    }
    // Keep the current projection mounted during polling. Toggling loading on
    // every refresh temporarily removes the version rows and makes the first
    // step visibly flash while the three-second poll is in flight.
    if (!hasLoadedRef.current) setLoading(true);
    try {
      const options = api.executionOptions(spaceId);
      const results = await Promise.allSettled([
        api.compileJobs(spaceId),
        api.schemas(spaceId),
        api.sources(spaceId, { limit: 100 }),
        options.then((o) => ({ items: o.prompt_versions })),
        options.then((o) => ({ items: o.model_profiles })),
      ]);
      if (epoch !== loadEpoch.current) return;
      const [jobResult, schemaResult, sourceResult, promptResult, modelResult] =
        results;
      const failures = results.filter(
        (result): result is PromiseRejectedResult =>
          result.status === "rejected",
      );
      if (jobResult.status === "fulfilled") {
        setJobs(jobResult.value.items);
        setSelected((current) =>
          current
            ? (jobResult.value.items.find((item) => item.id === current.id) ??
              null)
            : current,
        );
      } else {
        setJobs([]);
        setSelected(null);
      }
      if (schemaResult.status === "fulfilled") {
        const publishedSchemas = schemaResult.value.items.filter(
          (item) => item.status === "PUBLISHED",
        );
        setSchemas(publishedSchemas);
        setSchemaId((value) =>
          publishedSchemas.some((item) => item.id === value)
            ? value
            : publishedSchemas[0]?.id || "",
        );
      } else {
        setSchemas([]);
        setSchemaId("");
      }
      if (sourceResult.status === "fulfilled") {
        setSourcesUnavailable(false);
        setSources(sourceResult.value.items);
        const availableVersionIds = new Set(
          sourceResult.value.items.flatMap((source) =>
            source.versions
              .filter((version) =>
                ["PARSED", "PARTIAL"].includes(version.status),
              )
              .map((version) => version.id),
          ),
        );
        setSourceIds((current) =>
          current.filter((id) => availableVersionIds.has(id)),
        );
      } else {
        setSourcesUnavailable(true);
        setSources([]);
        setSourceIds([]);
      }
      if (promptResult.status === "fulfilled") {
        setPrompts(promptResult.value.items);
        setPromptId((value) =>
          promptResult.value.items.some((item) => item.id === value)
            ? value
            : promptResult.value.items[0]?.id || "",
        );
      } else {
        setPrompts([]);
        setPromptId("");
      }
      if (modelResult.status === "fulfilled") {
        setModels(modelResult.value.items);
        setModelId((value) =>
          modelResult.value.items.some((item) => item.id === value)
            ? value
            : modelResult.value.items.find(
                (item) => item.provider === "nexweave.local",
              )?.id ||
              modelResult.value.items[0]?.id ||
              "",
        );
      } else {
        setModels([]);
        setModelId("");
      }
      setError(
        failures.length
          ? "部分编译资源暂时无法读取；已保留可用内容，请重试。"
          : "",
      );
    } catch (cause) {
      if (epoch === loadEpoch.current)
        setError(messageOf(cause, "无法读取编译中心。"));
    } finally {
      if (epoch === loadEpoch.current) {
        hasLoadedRef.current = true;
        setLoading(false);
      }
    }
  }, [api, spaceId]);

  useEffect(() => {
    void load();
    if (!spaceId) return;
    const timer = window.setInterval(() => void load(), 3000);
    return () => {
      window.clearInterval(timer);
    };
  }, [load, spaceId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      loading ||
      busy ||
      !spaceId ||
      !sourceIds.length ||
      !schemaId ||
      !promptId ||
      !modelId
    )
      return;
    setBusy(true);
    try {
      const job = await api.createCompileJob(spaceId, {
        schema_version_id: schemaId,
        source_version_ids: sourceIds,
        prompt_version_id: promptId,
        model_profile_id: modelId,
        mode,
      });
      setSelected(job);
      setNotice("编译任务已提交。任务完成后会生成可审核草稿，不会自动发布。");
      await load();
    } catch (cause) {
      setError(messageOf(cause, "无法创建编译任务。"));
    } finally {
      setBusy(false);
    }
  }

  async function inspect(job: CompileJob) {
    try {
      setSelected(await api.compileJob(job.id));
    } catch (cause) {
      setError(messageOf(cause, "无法读取编译轨迹。"));
    }
  }

  async function retry(job: CompileJob) {
    if (busy || loading || !spaceId) return;
    setBusy(true);
    try {
      const retried = await api.createCompileJob(spaceId, {
        schema_version_id: job.schema_version_id,
        source_version_ids: job.sources.map(
          (source) => source.source_version_id,
        ),
        prompt_version_id: job.prompt_version_id,
        model_profile_id: job.model_profile_id,
        mode: "RECOMPILE",
        scope: { ...job.scope, retry_of_compile_job_id: job.id },
      });
      setSelected(retried);
      await load();
    } catch (cause) {
      setError(messageOf(cause, "无法重试编译任务。"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content-page">
      <PageHeader
        title="编译中心"
        description="选择已解析资料和知识模型，完成前置检查后生成可审核的知识草稿。"
      />
      {notice && (
        <div className="notice-banner" role="status">
          {notice}
        </div>
      )}
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="编译任务必须绑定到一个知识空间；请从左侧空间选择器进入工作区。"
        />
      )}
      <form className="compile-workflow" onSubmit={submit}>
        <section className="workflow-step">
          <span className="workflow-step-number">1</span>
          <div>
            <h2>选择知识版本</h2>
            <p>选择本次要转换为结构化知识的已解析资料。</p>
            <fieldset>
              <legend>
                可用资料版本 · {loading ? "读取中" : `${versions.length} 个`}
              </legend>
              {!loading &&
                versions.map((version) => (
                  <label className="check-row" key={version.id}>
                    <input
                      type="checkbox"
                      checked={sourceIds.includes(version.id)}
                      onChange={(event) =>
                        setSourceIds((current) =>
                          event.target.checked
                            ? [...current, version.id]
                            : current.filter((id) => id !== version.id),
                        )
                      }
                    />
                    {labelForVersion(version, sources)} ·{" "}
                    <StatusPill value={version.status} />
                  </label>
                ))}
              {loading && (
                <p className="workflow-loading" role="status">
                  正在读取资料、解析状态与编译配置…
                </p>
              )}
              {!loading && !versions.length && (
                <EmptyState
                  title={
                    sourcesUnavailable
                      ? "暂时无法读取资料版本"
                      : "没有可编译的资料"
                  }
                  description={
                    sourcesUnavailable
                      ? "资料目录请求没有完成；先重试读取，避免把暂时不可见误判为空目录。"
                      : "先在资料中心导入并完成解析，再返回这里开始编译。"
                  }
                  primaryAction={
                    sourcesUnavailable ? (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => void load()}
                      >
                        重试读取
                      </button>
                    ) : onNavigate ? (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => onNavigate("sources")}
                      >
                        前往资料中心 →
                      </button>
                    ) : (
                      <a className="btn" href="/sources">
                        前往资料中心 →
                      </a>
                    )
                  }
                />
              )}
            </fieldset>
          </div>
        </section>
        <section className="workflow-step">
          <span className="workflow-step-number">2</span>
          <div>
            <h2>选择编译配置</h2>
            <div className="form-grid two">
              <label>
                知识模型
                <select
                  value={schemaId}
                  onChange={(event) => setSchemaId(event.target.value)}
                  required
                >
                  <option value="">请选择已发布模型</option>
                  {schemas.map((schema) => (
                    <option key={schema.id} value={schema.id}>
                      {schema.schema_key} · {schema.semantic_version}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                编译方式
                <select
                  value={mode}
                  onChange={(event) =>
                    setMode(event.target.value as CompileJob["mode"])
                  }
                >
                  <option value="FULL">完整编译</option>
                  <option value="INCREMENTAL">增量编译</option>
                  <option value="SOURCE_SCOPED">仅选定资料</option>
                  <option value="RECOMPILE">重新编译</option>
                </select>
              </label>
            </div>
            <section
              className="compile-model-settings"
              aria-label="模型与提示词配置"
            >
              <p>模型与提示词</p>
              <div className="form-grid two">
                <label>
                  提示词版本
                  <select
                    value={promptId}
                    onChange={(event) => setPromptId(event.target.value)}
                    required
                  >
                    <option value="">请选择</option>
                    {prompts.map((prompt) => (
                      <option key={prompt.id} value={prompt.id}>
                        {prompt.prompt_key} · r{prompt.revision}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  模型配置
                  <select
                    value={modelId}
                    onChange={(event) => setModelId(event.target.value)}
                    required
                  >
                    <option value="">请选择</option>
                    {models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.model_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>
          </div>
        </section>
        <section className="workflow-step">
          <span className="workflow-step-number">3</span>
          <div>
            <h2>前置条件检查</h2>
            <ul className="preflight-list">
              <li className={sourceIds.length ? "ready" : "waiting"}>
                已选择 {sourceIds.length} 个资料版本
              </li>
              <li className={schemaId ? "ready" : "waiting"}>
                {schemaId ? "已选择发布知识模型" : "待选择发布知识模型"}
              </li>
              <li className={promptId && modelId ? "ready" : "waiting"}>
                {promptId && modelId ? "编译配置完整" : "待补全模型与提示词"}
              </li>
            </ul>
          </div>
        </section>
        <div className="workflow-submit">
          <span>
            <strong>下一步：</strong>编译输出将进入审核前草稿，不会直接发布。
          </span>
          <button
            className="primary"
            disabled={
              loading ||
              busy ||
              !sourceIds.length ||
              !schemaId ||
              !promptId ||
              !modelId
            }
            type="submit"
          >
            {busy ? "正在提交…" : "开始编译"}
          </button>
        </div>
      </form>
      <div className="data-card">
        <h2>运行记录</h2>
        {!jobs.length ? (
          <EmptyState
            title="还没有编译记录"
            description="完成上方三个步骤并开始编译后，运行状态和结果会显示在这里。"
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>模式</th>
                <th>状态</th>
                <th>进度</th>
                <th>对象</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{new Date(job.created_at).toLocaleString()}</td>
                  <td>{compileModeLabel(job.mode)}</td>
                  <td>
                    <StatusPill value={job.status} />
                  </td>
                  <td>{job.progress}%</td>
                  <td>
                    {String(
                      (
                        job.result_summary.stats as
                          | Record<string, unknown>
                          | undefined
                      )?.entities ?? "—",
                    )}
                  </td>
                  <td>
                    <button type="button" onClick={() => void inspect(job)}>
                      轨迹
                    </button>
                    {["FAILED", "PARTIAL_FAILED", "CANCELED"].includes(
                      job.status,
                    ) && (
                      <button
                        type="button"
                        disabled={busy || loading}
                        onClick={() => void retry(job)}
                      >
                        新任务重试
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {selected && (
        <div className="data-card">
          <h2>CompileJob 轨迹</h2>
          {selected.status === "SUCCEEDED" && (
            <div className="compile-next-step" role="status">
              <strong>编译完成：</strong>草稿已生成，下一步请到 Wiki
              核对内容，再进入审核；当前仍未发布。
              <div>
                {onNavigate ? (
                  <>
                    <button type="button" onClick={() => onNavigate("wiki")}>
                      打开 Wiki
                    </button>
                    <button type="button" onClick={() => onNavigate("reviews")}>
                      打开审核
                    </button>
                  </>
                ) : (
                  <>
                    <a className="btn" href="/wiki">
                      打开 Wiki
                    </a>
                    <a className="btn" href="/reviews">
                      打开审核
                    </a>
                  </>
                )}
              </div>
            </div>
          )}
          <p>
            <code>{selected.input_fingerprint.slice(0, 20)}…</code>
          </p>
          <p>
            Provider：{String(selected.result_summary.provider ?? "等待执行")} ·
            外部 LLM：
            {String(selected.result_summary.external_llm_called ?? false)}
          </p>
          <TechnicalDetails summary="查看完整编译技术轨迹">
            <pre>
              {JSON.stringify(
                {
                  sources: selected.sources,
                  steps: selected.steps,
                  cost: selected.cost_summary,
                  result: selected.result_summary,
                },
                null,
                2,
              )}
            </pre>
          </TechnicalDetails>
        </div>
      )}
    </section>
  );
}

function labelForVersion(version: SourceVersion, sources: SourceDocument[]) {
  return (
    sources.find((source) => source.id === version.source_document_id)
      ?.display_name || version.filename
  );
}

function compileModeLabel(value: CompileJob["mode"]) {
  return (
    {
      FULL: "完整编译",
      INCREMENTAL: "增量编译",
      SOURCE_SCOPED: "选定资料",
      RECOMPILE: "重新编译",
    }[value] ?? value
  );
}
