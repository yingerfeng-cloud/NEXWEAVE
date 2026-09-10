import {
  useCallback,
  useEffect,
  useMemo,
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

export function CompileCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
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
  const [error, setError] = useState("");

  const versions = useMemo(
    () =>
      sources
        .flatMap((source) => source.versions)
        .filter((version) => ["PARSED", "PARTIAL"].includes(version.status)),
    [sources],
  );

  const load = useCallback(async () => {
    if (!spaceId) {
      setJobs([]);
      setSchemas([]);
      setSources([]);
      setPrompts([]);
      setModels([]);
      setSelected(null);
      setError("");
      return;
    }
    try {
      const [jobPage, schemaPage, sourcePage, promptPage, modelPage] =
        await Promise.all([
          api.compileJobs(spaceId),
          api.schemas(spaceId),
          api.sources(spaceId, { limit: 100 }),
          api.listGovernance("prompt-versions"),
          api.listGovernance("model-profiles"),
        ]);
      setJobs(jobPage.items);
      const publishedSchemas = schemaPage.items.filter(
        (item) => item.status === "PUBLISHED",
      );
      setSchemas(publishedSchemas);
      setSources(sourcePage.items);
      setPrompts(promptPage.items);
      setModels(modelPage.items);
      setSchemaId((value) =>
        publishedSchemas.some((item) => item.id === value)
          ? value
          : publishedSchemas[0]?.id || "",
      );
      setPromptId((value) =>
        promptPage.items.some((item) => item.id === value)
          ? value
          : promptPage.items[0]?.id || "",
      );
      setModelId((value) =>
        modelPage.items.some((item) => item.id === value)
          ? value
          : modelPage.items.find((item) => item.provider === "nexweave.local")
              ?.id ||
            modelPage.items[0]?.id ||
            "",
      );
      const availableVersionIds = new Set(
        sourcePage.items.flatMap((source) =>
          source.versions
            .filter((version) => ["PARSED", "PARTIAL"].includes(version.status))
            .map((version) => version.id),
        ),
      );
      setSourceIds((current) =>
        current.filter((id) => availableVersionIds.has(id)),
      );
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取编译中心。"));
    }
  }, [api, spaceId]);

  useEffect(() => {
    if (!spaceId) return;
    void load();
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [load, spaceId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
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
              <legend>可用资料版本</legend>
              {versions.map((version) => (
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
              {!versions.length && (
                <EmptyState
                  title="没有可编译的资料"
                  description="先在资料中心导入并完成解析，再返回这里开始编译。"
                  primaryAction={
                    <a className="btn" href="/sources">
                      前往资料中心 →
                    </a>
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
              busy || !sourceIds.length || !schemaId || !promptId || !modelId
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
                        disabled={busy}
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
