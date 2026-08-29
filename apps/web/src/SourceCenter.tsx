import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, NexweaveApi } from "./api";
import type {
  AnchorStatus,
  DataClassification,
  DocumentSegment,
  ImportBatch,
  Locator,
  ParseJob,
  Principal,
  PreviewResponse,
  SourceDocument,
  SourceFilters,
  SourceUploadComplete,
  SourceUploadSession,
  SourceVersion,
} from "./types";

const CLASSIFICATIONS: DataClassification[] = [
  "PUBLIC",
  "INTERNAL",
  "CONFIDENTIAL",
  "HIGHLY_RESTRICTED",
];

const FILE_TYPES = [
  ["", "全部类型"],
  ["application/pdf", "PDF"],
  [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "DOCX",
  ],
  ["text/markdown", "Markdown"],
  ["text/plain", "TXT"],
  ["text/csv", "CSV"],
  ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "XLSX"],
] as const;

type SourceRoute =
  | { kind: "list" }
  | { kind: "source"; sourceId: string }
  | { kind: "version"; sourceId: string; versionId: string }
  | { kind: "preview"; versionId: string }
  | { kind: "unknown" };

export function SourceCenter({
  api,
  principal,
  spaceId,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaceId: string;
}) {
  const [path, setPath] = useState(() => location.pathname + location.search);
  const route = useMemo(() => readSourceRoute(path.split("?")[0]), [path]);

  const navigate = useCallback((target: string) => {
    history.pushState({}, "", target);
    setPath(location.pathname + location.search);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const restore = () => setPath(location.pathname + location.search);
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  useEffect(() => {
    document.querySelector<HTMLElement>(".source-page h1")?.focus();
  }, [path]);

  if (!spaceId) {
    return (
      <SourcePage title="资料中心" description="请先选择一个知识空间。">
        <Empty text="当前没有可用的知识空间" />
      </SourcePage>
    );
  }

  if (route.kind === "list") {
    return (
      <SourceListPage
        api={api}
        principal={principal}
        spaceId={spaceId}
        pathKey={path}
        onNavigate={navigate}
      />
    );
  }
  if (route.kind === "source") {
    return (
      <SourceDetailPage
        api={api}
        principal={principal}
        sourceId={route.sourceId}
        onNavigate={navigate}
      />
    );
  }
  if (route.kind === "version") {
    return (
      <VersionDetailPage
        api={api}
        principal={principal}
        sourceId={route.sourceId}
        versionId={route.versionId}
        pathKey={path}
        onNavigate={navigate}
      />
    );
  }
  if (route.kind === "preview") {
    return (
      <PreviewPage
        api={api}
        versionId={route.versionId}
        pathKey={path}
        onNavigate={navigate}
      />
    );
  }
  return (
    <SourcePage title="资料页面不存在" description="该资料中心路径无法识别。">
      <button className="primary" onClick={() => navigate("/sources")}>
        返回资料中心
      </button>
    </SourcePage>
  );
}

function SourceListPage({
  api,
  principal,
  spaceId,
  pathKey,
  onNavigate,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaceId: string;
  pathKey: string;
  onNavigate: (path: string) => void;
}) {
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const filters = useMemo(() => readSourceFilters(pathKey), [pathKey]);
  const batchId = useMemo(
    () => new URL(pathKey, location.origin).searchParams.get("batch_id") ?? "",
    [pathKey],
  );
  const canUpload = canManageSources(principal);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const page = await api.sources(spaceId, { ...filters, limit: 50 });
      setSources(page.items);
      setNextCursor(page.next_cursor ?? null);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, filters, spaceId]);

  useEffect(() => void load(), [load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const query = new URLSearchParams();
    for (const key of ["search", "type", "status", "classification"]) {
      const value = String(data.get(key) ?? "").trim();
      if (value) query.set(key, value);
    }
    onNavigate(`/sources${query.size ? `?${query}` : ""}`);
  }

  const counts = {
    active: sources.filter((source) => source.status === "ACTIVE").length,
    registered: sources.filter((source) => source.status === "REGISTERED")
      .length,
    archived: sources.filter((source) => source.status === "ARCHIVED").length,
  };

  return (
    <SourcePage
      title="资料中心"
      description="不可变 Raw、版本化解析与可复现定位。列表、筛选和上传结果均来自 M3 API。"
    >
      <div className="metric-grid source-metrics">
        <Metric value={sources.length} label="当前页资料" detail="稳定游标" />
        <Metric value={counts.active} label="有效资料" detail="逻辑资料状态" />
        <Metric
          value={counts.registered}
          label="待激活"
          detail="REGISTERED"
          tone="warning"
        />
        <Metric
          value={counts.archived}
          label="已归档"
          detail="Raw 与历史仍保留"
        />
      </div>

      <Panel title="筛选资料">
        <form className="source-filter" onSubmit={applyFilters}>
          <label>
            搜索
            <input
              name="search"
              type="search"
              defaultValue={filters.search}
              placeholder="名称、说明或标签"
            />
          </label>
          <label>
            文件类型
            <select name="type" defaultValue={filters.type}>
              {FILE_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            资料状态
            <select name="status" defaultValue={filters.status}>
              <option value="">全部状态</option>
              <option value="REGISTERED">REGISTERED</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="ARCHIVED">ARCHIVED</option>
            </select>
          </label>
          <label>
            筛选密级
            <select name="classification" defaultValue={filters.classification}>
              <option value="">全部密级</option>
              {CLASSIFICATIONS.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <div className="source-filter-actions">
            <button className="primary">应用筛选</button>
            <button type="button" onClick={() => onNavigate("/sources")}>
              清除
            </button>
          </div>
        </form>
      </Panel>

      {canUpload && (
        <UploadPanel
          api={api}
          initialBatchId={batchId}
          spaceId={spaceId}
          onImported={() => void load()}
          onNavigate={onNavigate}
        />
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      <Panel title={`资料列表 · ${sources.length}`}>
        {loading ? (
          <Loading text="正在读取资料目录…" />
        ) : sources.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>资料</th>
                  <th>密级</th>
                  <th>状态</th>
                  <th>来源等级 / 标签</th>
                  <th>更新时间</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => {
                  return (
                    <tr key={source.id}>
                      <td>
                        <button
                          className="source-link"
                          onClick={() => onNavigate(`/sources/${source.id}`)}
                        >
                          <strong>{source.display_name}</strong>
                          <small>{source.description || "暂无来源说明"}</small>
                        </button>
                      </td>
                      <td>
                        <Status value={source.classification} />
                      </td>
                      <td>
                        <Status value={source.status} />
                      </td>
                      <td>
                        <span className="version-cell">
                          {source.source_level || "未设置来源等级"}
                          <small>
                            {source.tags.length
                              ? source.tags.join(" · ")
                              : "无标签"}
                          </small>
                        </span>
                      </td>
                      <td>{formatDate(source.updated_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            text={
              hasFilters(filters)
                ? "没有符合当前筛选的资料"
                : "当前空间尚无资料，可以从上方导入"
            }
          />
        )}
        {nextCursor && (
          <div className="pagination">
            <button
              onClick={() => {
                const query = new URLSearchParams(location.search);
                query.set("cursor", nextCursor);
                onNavigate(`/sources?${query}`);
              }}
            >
              下一页
            </button>
          </div>
        )}
      </Panel>

      <FutureBoundary />
    </SourcePage>
  );
}

type UploadStage =
  | "CHECKSUM"
  | "UPLOADING"
  | "PROCESSING"
  | "PARTIAL"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELED";

type UploadOutcome = {
  filename: string;
  stage: UploadStage;
  detail: string;
  result?: SourceUploadComplete;
};

function UploadPanel({
  api,
  initialBatchId,
  replacement,
  spaceId,
  onImported,
  onNavigate,
}: {
  api: NexweaveApi;
  initialBatchId: string;
  replacement?: {
    sourceId: string;
    versionId: string;
    classification: DataClassification;
  };
  spaceId: string;
  onImported: () => void;
  onNavigate: (path: string) => void;
}) {
  const [outcomes, setOutcomes] = useState<UploadOutcome[]>([]);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [batchId, setBatchId] = useState(initialBatchId);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const canceled = useRef(false);
  const activeUpload = useRef<AbortController | null>(null);

  const update = (filename: string, patch: Partial<UploadOutcome>) =>
    setOutcomes((current) =>
      current.map((item) =>
        item.filename === filename ? { ...item, ...patch } : item,
      ),
    );

  const refreshBatch = useCallback(async () => {
    if (!batchId) return;
    try {
      const refreshed = await api.importBatch(batchId);
      setBatch(refreshed);
      setOutcomes(outcomesFromBatch(refreshed));
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }, [api, batchId]);

  useEffect(() => {
    if (!batchId) return;
    let active = true;
    let timer: number | undefined;
    const restore = async () => {
      try {
        const refreshed = await api.importBatch(batchId);
        if (!active) return;
        setBatch(refreshed);
        setOutcomes(outcomesFromBatch(refreshed));
        if (["CREATED", "UPLOADING", "PROCESSING"].includes(refreshed.status)) {
          timer = window.setTimeout(() => void restore(), 2_000);
        }
      } catch (nextError) {
        if (active) setError(messageOf(nextError));
      }
    };
    void restore();
    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [api, batchId]);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const files = Array.from(
      (form.elements.namedItem("files") as HTMLInputElement).files ?? [],
    );
    if (!files.length) return;
    canceled.current = false;
    setWorking(true);
    setError("");
    setBatch(null);
    setOutcomes(
      files.map((file) => ({
        filename: file.name,
        stage: "CHECKSUM",
        detail: "正在计算 SHA-256",
      })),
    );

    let importBatch: ImportBatch | null = null;
    try {
      if (files.length > 1 && !replacement) {
        importBatch = await api.createImportBatch(
          spaceId,
          String(
            data.get("batch_name") || `批量导入 ${formatDate(new Date())}`,
          ),
        );
        setBatch(importBatch);
        setBatchId(importBatch.id);
        const query = new URLSearchParams(location.search);
        query.set("batch_id", importBatch.id);
        history.replaceState({}, "", `/sources?${query}`);
      }
      for (const file of files) {
        if (canceled.current) {
          update(file.name, { stage: "CANCELED", detail: "用户已取消" });
          continue;
        }
        let session: SourceUploadSession | null = null;
        try {
          const checksum = await sha256(file);
          update(file.name, {
            stage: "UPLOADING",
            detail: `校验值 ${shortHash(checksum)} · 正在上传 Raw`,
          });
          session = await api.createSourceUpload(spaceId, {
            filename: file.name,
            content_type: file.type || inferContentType(file.name),
            expected_size: file.size,
            expected_checksum: checksum,
            display_name: sourceName(file.name),
            description: String(data.get("description") ?? ""),
            classification: data.get("classification"),
            source_level: String(data.get("source_level") ?? "") || null,
            tags: splitTags(String(data.get("tags") ?? "")),
            import_batch_id: importBatch?.id ?? null,
            source_document_id: replacement?.sourceId ?? null,
            supersedes_source_version_id: replacement?.versionId ?? null,
          });
          activeUpload.current = new AbortController();
          await api.uploadSourceContent(
            session,
            file,
            activeUpload.current.signal,
          );
          update(file.name, {
            stage: "PROCESSING",
            detail: "Raw 已上传，服务端正在复核并登记解析任务",
          });
          const result = await api.completeSourceUpload(
            session.id,
            checksum,
            file.size,
          );
          update(file.name, {
            stage: "PROCESSING",
            detail: `ParseJob ${shortId(result.parse_job_id)} 已进入 ${result.version_status}`,
            result,
          });
        } catch (nextError) {
          const aborted =
            nextError instanceof DOMException &&
            nextError.name === "AbortError";
          if (aborted && session) {
            await api.abortSourceUpload(session.id).catch(() => undefined);
          }
          update(file.name, {
            stage: aborted ? "CANCELED" : "FAILED",
            detail: aborted ? "用户已取消当前上传" : messageOf(nextError),
          });
        } finally {
          activeUpload.current = null;
        }
      }
      if (importBatch) {
        try {
          const refreshed = await api.importBatch(importBatch.id);
          setBatch(refreshed);
          setOutcomes((current) =>
            current.map((outcome) => {
              const item = refreshed.items.find(
                (candidate) => candidate.filename === outcome.filename,
              );
              return item
                ? {
                    ...outcome,
                    stage: item.status,
                    detail: item.safe_detail || batchStageLabel(item.status),
                  }
                : outcome;
            }),
          );
        } catch {
          // Per-file API outcomes remain visible if a batch projection is still converging.
        }
      }
      onImported();
      form.reset();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  function cancel() {
    canceled.current = true;
    activeUpload.current?.abort();
  }

  return (
    <Panel title={replacement ? "上传替代版本" : "受控导入"}>
      <form className="upload-form" onSubmit={start}>
        <label className="upload-drop">
          {replacement ? "选择新的替代文件" : "选择一个或多个文件"}
          <input
            name="files"
            type="file"
            multiple={!replacement}
            accept=".pdf,.docx,.md,.markdown,.txt,.csv,.xlsx"
            required
          />
          <small>PDF · DOCX · Markdown · TXT · CSV · XLSX</small>
        </label>
        {!replacement && (
          <label>
            批次名称
            <input name="batch_name" placeholder="仅多文件导入时使用" />
          </label>
        )}
        <label>
          资料密级
          <select
            name="classification"
            defaultValue={replacement?.classification ?? "INTERNAL"}
          >
            {CLASSIFICATIONS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        {!replacement && (
          <>
            <label>
              来源等级
              <input name="source_level" placeholder="可审计元数据，非置信度" />
            </label>
            <label>
              标签
              <input name="tags" placeholder="用逗号分隔" />
            </label>
            <label className="wide">
              来源说明
              <textarea name="description" />
            </label>
          </>
        )}
        <div className="form-actions wide">
          <button className="primary" disabled={working}>
            {working
              ? "正在导入…"
              : replacement
                ? "登记替代版本"
                : "开始受控导入"}
          </button>
          {working && (
            <button type="button" className="danger" onClick={cancel}>
              取消剩余上传
            </button>
          )}
        </div>
      </form>
      {error && <ErrorState message={error} />}
      {batch && (
        <div className="batch-summary" aria-live="polite">
          <span>批次 {shortId(batch.id)}</span>
          <Status value={batch.status} />
          <small>
            {Object.entries(batch.item_summary)
              .map(([key, value]) => `${key} ${value}`)
              .join(" · ") || "逐项执行中"}
          </small>
          <button onClick={() => void refreshBatch()}>刷新批次结果</button>
        </div>
      )}
      {outcomes.length > 0 && (
        <ol className="upload-results" aria-label="逐文件导入结果">
          {outcomes.map((outcome) => (
            <li key={outcome.filename}>
              <Status value={outcome.stage} />
              <div>
                <strong>{outcome.filename}</strong>
                <small>{outcome.detail}</small>
              </div>
              {outcome.result && (
                <button
                  onClick={() =>
                    onNavigate(`/sources/${outcome.result?.source_id}`)
                  }
                >
                  查看资料
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
      <p className="truth-note">
        {replacement
          ? "替代会创建新的 SourceVersion、对象 key 与 ParseJob；旧 Raw、解析和 Anchor 仍被保留。"
          : "complete 只表示 Raw 已登记并创建真实 ParseJob；解析完成、部分失败与 OCR_REQUIRED 以服务端状态为准。"}
      </p>
    </Panel>
  );
}

function SourceDetailPage({
  api,
  principal,
  sourceId,
  onNavigate,
}: {
  api: NexweaveApi;
  principal: Principal;
  sourceId: string;
  onNavigate: (path: string) => void;
}) {
  const [source, setSource] = useState<SourceDocument | null>(null);
  const [jobs, setJobs] = useState<Record<string, ParseJob>>({});
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const canManage = canManageSources(principal);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const value = await api.source(sourceId);
      setSource(value);
      const ids = [
        ...new Set(
          value.versions.flatMap((version) => [
            version.active_parse_job_id,
            version.latest_parse_job_id,
          ]),
        ),
      ].filter((value): value is string => Boolean(value));
      const loaded = await Promise.all(ids.map((id) => api.parseJob(id)));
      setJobs(Object.fromEntries(loaded.map((job) => [job.id, job])));
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, sourceId]);

  useEffect(() => void load(), [load]);

  async function archive() {
    if (!source || !confirm("归档资料不会删除 Raw 与历史解析。确认继续？"))
      return;
    setWorking(true);
    setError("");
    try {
      await api.archiveSource(source);
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  const replaceableVersion = source
    ? latestVersion(source.versions)
    : undefined;

  return (
    <SourcePage
      title={source?.display_name ?? "资料详情"}
      description="逻辑资料、不可变版本链与解析执行的可追溯视图。"
      back={{ label: "返回资料列表", path: "/sources" }}
      onNavigate={onNavigate}
    >
      {error && <ErrorState message={error} onRetry={load} />}
      {loading ? (
        <Loading text="正在恢复资料详情…" />
      ) : source ? (
        <>
          <Panel title="资料元数据与允许动作">
            <div className="source-summary">
              <Fact label="状态">
                <Status value={source.status} />
              </Fact>
              <Fact label="密级">
                <Status value={source.classification} />
              </Fact>
              <Fact label="来源等级">{source.source_level || "未设置"}</Fact>
              <Fact label="有效期">
                {source.valid_until ? formatDate(source.valid_until) : "未设置"}
              </Fact>
              <Fact label="标签">
                {source.tags.length ? source.tags.join(" · ") : "无"}
              </Fact>
              <Fact label="聚合版本">v{source.version}</Fact>
              <Fact label="登记 / 更新">
                {formatDate(source.created_at)} /{" "}
                {formatDate(source.updated_at)}
              </Fact>
              <Fact label="审计 actor">
                {shortId(source.created_by)} / {shortId(source.updated_by)}
              </Fact>
            </div>
            <p className="source-description">
              {source.description || "暂无来源说明"}
            </p>
            <div className="source-actions" aria-label="资料允许动作">
              <button onClick={() => void load()} disabled={working}>
                刷新状态
              </button>
              {canManage && source.status !== "ARCHIVED" && (
                <button
                  className="danger"
                  onClick={() => void archive()}
                  disabled={working}
                >
                  归档资料
                </button>
              )}
              {!canManage && <span>当前身份仅可查看</span>}
            </div>
            <p className="truth-note">
              界面动作按身份提示；服务端仍会重新执行
              tenant、space、密级、状态与权限校验。
            </p>
          </Panel>

          {canManage &&
            source.status !== "ARCHIVED" &&
            replaceableVersion &&
            replaceableVersion.status !== "SUPERSEDED" && (
              <UploadPanel
                api={api}
                initialBatchId=""
                replacement={{
                  sourceId: source.id,
                  versionId: replaceableVersion.id,
                  classification: source.classification,
                }}
                spaceId={source.space_id}
                onImported={() => void load()}
                onNavigate={onNavigate}
              />
            )}

          <Panel title={`不可变版本链 · ${source.versions.length}`}>
            {source.versions.length ? (
              <ol className="version-chain">
                {[...source.versions].reverse().map((version) => {
                  const active = version.active_parse_job_id
                    ? jobs[version.active_parse_job_id]
                    : undefined;
                  const latest = version.latest_parse_job_id
                    ? jobs[version.latest_parse_job_id]
                    : undefined;
                  return (
                    <li key={version.id}>
                      <button
                        className="version-main"
                        onClick={() =>
                          onNavigate(
                            `/sources/${source.id}/versions/${version.id}`,
                          )
                        }
                      >
                        <span>
                          <strong>{version.filename}</strong>
                          <small>
                            {formatBytes(version.size)} · {version.content_type}
                          </small>
                        </span>
                        <Status value={version.status} />
                      </button>
                      <code title={version.checksum}>{version.checksum}</code>
                      <div className="parse-pointer-grid">
                        <ParsePointer label="ACTIVE PARSEJOB" job={active} />
                        <ParsePointer label="LATEST PARSEJOB" job={latest} />
                      </div>
                      {latest?.failure_units.length ? (
                        <FailureUnits items={latest.failure_units} />
                      ) : null}
                      {version.supersedes_source_version_id && (
                        <small className="chain-relation">
                          替代版本{" "}
                          {shortId(version.supersedes_source_version_id)}
                        </small>
                      )}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <Empty text="尚无已登记的 SourceVersion" />
            )}
          </Panel>
        </>
      ) : null}
    </SourcePage>
  );
}

function VersionDetailPage({
  api,
  principal,
  sourceId,
  versionId,
  pathKey,
  onNavigate,
}: {
  api: NexweaveApi;
  principal: Principal;
  sourceId: string;
  versionId: string;
  pathKey: string;
  onNavigate: (path: string) => void;
}) {
  const [version, setVersion] = useState<SourceVersion | null>(null);
  const [jobs, setJobs] = useState<ParseJob[]>([]);
  const [segments, setSegments] = useState<DocumentSegment[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const canManage = canManageSources(principal);
  const tab = useMemo(
    () => new URL(pathKey, location.origin).searchParams.get("tab") || "raw",
    [pathKey],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const raw = await api.sourceVersion(sourceId, versionId);
      setVersion(raw);
      const ids = [
        ...new Set([raw.active_parse_job_id, raw.latest_parse_job_id]),
      ].filter((value): value is string => Boolean(value));
      const [loadedJobs, segmentPage] = await Promise.all([
        Promise.all(ids.map((id) => api.parseJob(id))),
        api.sourceSegments(versionId, {
          parse_job_id: raw.active_parse_job_id ?? undefined,
          limit: 100,
        }),
      ]);
      setJobs(loadedJobs);
      setSegments(segmentPage.items);
      setNextCursor(segmentPage.next_cursor ?? null);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, sourceId, versionId]);

  useEffect(() => void load(), [load]);

  function selectTab(next: string) {
    onNavigate(
      `/sources/${sourceId}/versions/${versionId}?${new URLSearchParams({ tab: next })}`,
    );
  }

  async function download() {
    if (!version) return;
    setWorking(true);
    setError("");
    try {
      const blob = await api.downloadSourceVersion(version.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = version.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function reparse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!version) return;
    const data = new FormData(event.currentTarget);
    setWorking(true);
    setError("");
    try {
      await api.reparseSourceVersion(version, {
        parser_id: data.get("parser_id"),
        parser_version: data.get("parser_version"),
        config: {},
        ocr_provider_id: null,
        ocr_provider_version: null,
      });
      await load();
      selectTab("parse");
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function retry(job: ParseJob) {
    setWorking(true);
    setError("");
    try {
      await api.retryParseJob(job);
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function cancelParse(job: ParseJob) {
    setWorking(true);
    setError("");
    try {
      await api.cancelParseJob(job);
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function invalidate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!version) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setWorking(true);
    setError("");
    try {
      await api.invalidateSourceVersion(version, {
        reason_code: String(data.get("reason_code")),
        reason: String(data.get("reason")),
        policy_version: String(data.get("policy_version")),
      });
      form.reset();
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  const activeJob = jobs.find((job) => job.id === version?.active_parse_job_id);
  const latestJob = jobs.find((job) => job.id === version?.latest_parse_job_id);
  const canRetry =
    latestJob &&
    ["FAILED", "PARTIAL_FAILED"].includes(latestJob.status) &&
    latestJob.failure_units.some((item) => item.retryable);

  return (
    <SourcePage
      title={version?.filename ?? "SourceVersion"}
      description="Raw 永不原地修改；每次 reparse 创建新的 ParseJob，失败不会破坏已有 active 结果。"
      back={{ label: "返回资料详情", path: `/sources/${sourceId}` }}
      onNavigate={onNavigate}
    >
      {error && <ErrorState message={error} onRetry={load} />}
      {loading ? (
        <Loading text="正在读取版本与解析投影…" />
      ) : version ? (
        <>
          <div className="tabs" role="tablist" aria-label="版本详情视图">
            {[
              ["raw", "Raw 元数据"],
              ["parse", "Parse 历史"],
              ["segments", `Segments · ${segments.length}`],
            ].map(([value, label]) => (
              <button
                key={value}
                role="tab"
                aria-selected={tab === value}
                className={tab === value ? "active" : ""}
                onClick={() => selectTab(value)}
              >
                {label}
              </button>
            ))}
            <button
              onClick={() =>
                onNavigate(`/source-versions/${version.id}/preview`)
              }
            >
              安全预览
            </button>
          </div>

          {tab === "raw" && (
            <Panel title="不可变 Raw">
              <div className="source-summary">
                <Fact label="状态">
                  <Status value={version.status} />
                </Fact>
                <Fact label="密级">
                  <Status value={version.classification} />
                </Fact>
                <Fact label="大小">{formatBytes(version.size)}</Fact>
                <Fact label="MIME">{version.content_type}</Fact>
                <Fact label="对象版本">
                  {version.object_version_id || "存储未返回版本 ID"}
                </Fact>
                <Fact label="SourceVersion 聚合版本">v{version.version}</Fact>
                <Fact label="登记时间">{formatDate(version.created_at)}</Fact>
                <Fact label="登记 actor">{shortId(version.created_by)}</Fact>
              </div>
              <div className="checksum-card">
                <span>SHA-256</span>
                <code>{version.checksum}</code>
              </div>
              <div className="source-actions">
                <button disabled={working} onClick={() => void download()}>
                  受控下载 Raw
                </button>
              </div>
            </Panel>
          )}

          {tab === "parse" && (
            <>
              <Panel title="active / latest ParseJob">
                <div className="parse-pointer-grid">
                  <ParsePointer label="ACTIVE PARSEJOB" job={activeJob} />
                  <ParsePointer label="LATEST PARSEJOB" job={latestJob} />
                </div>
                {latestJob?.failure_units.length ? (
                  <FailureUnits items={latestJob.failure_units} />
                ) : null}
                {canManage && canRetry && (
                  <div className="source-actions">
                    <button
                      className="primary"
                      disabled={working}
                      onClick={() => void retry(latestJob)}
                    >
                      重试同一配置
                    </button>
                  </div>
                )}
                {canManage &&
                  latestJob &&
                  ["CREATED", "QUEUED", "RUNNING"].includes(
                    latestJob.status,
                  ) && (
                    <div className="source-actions">
                      <button
                        className="danger"
                        disabled={working}
                        onClick={() => void cancelParse(latestJob)}
                      >
                        取消解析
                      </button>
                    </div>
                  )}
              </Panel>
              {canManage && version.status !== "SUPERSEDED" && (
                <Panel title="重新解析">
                  <form className="inline-form" onSubmit={reparse}>
                    <label>
                      Parser
                      <input
                        name="parser_id"
                        defaultValue="nexweave.parser.builtin"
                        required
                      />
                    </label>
                    <label>
                      Parser 版本
                      <input
                        name="parser_version"
                        defaultValue="1.0.0"
                        required
                      />
                    </label>
                    <button className="primary" disabled={working}>
                      创建新 ParseJob
                    </button>
                  </form>
                  <p className="truth-note">
                    当前未选择 OCR Provider；扫描页将如实显示 OCR_REQUIRED /
                    PARTIAL_FAILED。
                  </p>
                </Panel>
              )}
            </>
          )}

          {tab === "segments" && (
            <Panel title={`active ParseJob Segments · ${segments.length}`}>
              {segments.length ? (
                <div className="segment-list">
                  {segments.map((segment) => (
                    <article key={segment.id}>
                      <header>
                        <span>#{segment.sequence}</span>
                        <Status value={segment.block_type} />
                        <code>{segment.structure_path}</code>
                      </header>
                      <p>
                        {segment.normalized_text ||
                          "正文存放于受控派生对象，未在列表内回显。"}
                      </p>
                      <footer>
                        {segmentPosition(segment)} · {segment.locators.length}{" "}
                        个定位器 · {shortHash(segment.text_checksum)}
                      </footer>
                    </article>
                  ))}
                </div>
              ) : (
                <Empty
                  text={
                    activeJob?.status === "PARTIAL_FAILED"
                      ? "部分解析尚未返回可展示 Segment，请查看失败单元"
                      : "当前 active ParseJob 尚无可展示 Segment"
                  }
                />
              )}
              {nextCursor && (
                <p className="truth-note">
                  当前仅展示前 100 个 Segment；后续页游标由 API 提供。
                </p>
              )}
            </Panel>
          )}

          {canManage && (
            <Panel title="追加失效事实">
              <form className="inline-form" onSubmit={invalidate}>
                <label>
                  原因代码
                  <input
                    name="reason_code"
                    placeholder="SOURCE_WITHDRAWN"
                    required
                  />
                </label>
                <label>
                  原因说明
                  <input name="reason" required />
                </label>
                <label>
                  策略版本
                  <input
                    name="policy_version"
                    placeholder="由当前治理策略提供"
                    required
                  />
                </label>
                <button className="danger" disabled={working}>
                  失效此版本
                </button>
              </form>
              <p className="truth-note">
                失效会追加事实并撤销 Anchor 内容访问，不会删除 Raw、Segment
                或历史审计。
              </p>
            </Panel>
          )}
        </>
      ) : null}
    </SourcePage>
  );
}

function PreviewPage({
  api,
  versionId,
  pathKey,
  onNavigate,
}: {
  api: NexweaveApi;
  versionId: string;
  pathKey: string;
  onNavigate: (path: string) => void;
}) {
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const anchorId = useMemo(
    () => new URL(pathKey, location.origin).searchParams.get("anchor_id") ?? "",
    [pathKey],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPreview(await api.sourcePreview(versionId, anchorId || undefined));
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [anchorId, api, versionId]);

  useEffect(() => void load(), [load]);

  function locate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(
      new FormData(event.currentTarget).get("anchor_id") ?? "",
    ).trim();
    const query = value ? `?${new URLSearchParams({ anchor_id: value })}` : "";
    onNavigate(`/source-versions/${versionId}/preview${query}`);
  }

  return (
    <SourcePage
      title="安全原文预览"
      description="预览由服务端重新授权并净化；客户端不会执行 HTML、脚本、宏、外链或嵌入对象。"
      back={{ label: "返回资料列表", path: "/sources" }}
      onNavigate={onNavigate}
    >
      <Panel title="Anchor 定位">
        <form className="inline-form" onSubmit={locate}>
          <label>
            Anchor ID
            <input
              name="anchor_id"
              defaultValue={anchorId}
              placeholder="留空查看 active ParseJob 安全预览"
            />
          </label>
          <button className="primary">定位并重新授权</button>
        </form>
      </Panel>
      {error && <ErrorState message={error} onRetry={load} />}
      {loading ? (
        <Loading text="正在重新授权并生成净化预览…" />
      ) : preview ? (
        <div className="preview-layout">
          <Panel title="定位状态">
            <div className="preview-status">
              <Status value={preview.anchor_status || "NO_ANCHOR"} />
              <p>{anchorExplanation(preview.anchor_status)}</p>
              <code>ParseJob {preview.parse_job_id}</code>
            </div>
            {preview.locator_results.length ? (
              <ol className="locator-results">
                {preview.locator_results.map((result, index) => (
                  <li key={`${locatorLabel(result.locator)}-${index}`}>
                    <span className={result.matched ? "hit" : "miss"}>
                      {result.matched ? "命中" : "未命中"}
                    </span>
                    <code>{locatorLabel(result.locator)}</code>
                    <small>{result.safe_detail}</small>
                  </li>
                ))}
              </ol>
            ) : (
              <Empty text="当前预览未指定 Anchor" />
            )}
          </Panel>
          <Panel title={`净化内容 · ${preview.content_type}`}>
            <pre className="sanitized-preview" tabIndex={0}>
              {preview.sanitized_content}
            </pre>
            <p className="truth-note">
              HTML 以文本方式呈现，避免客户端二次执行任何活动内容。
            </p>
          </Panel>
        </div>
      ) : null}
    </SourcePage>
  );
}

function SourcePage({
  title,
  description,
  back,
  onNavigate,
  children,
}: {
  title: string;
  description: string;
  back?: { label: string; path: string };
  onNavigate?: (path: string) => void;
  children: ReactNode;
}) {
  return (
    <section className="page source-page">
      {back && onNavigate && (
        <button className="back-link" onClick={() => onNavigate(back.path)}>
          ← {back.label}
        </button>
      )}
      <header className="page-title">
        <span>03 / M3</span>
        <div>
          <h1 tabIndex={-1}>{title}</h1>
          <p>{description}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <header>
        <h2>{title}</h2>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function Metric({
  value,
  label,
  detail,
  tone = "",
}: {
  value: number;
  label: string;
  detail: string;
  tone?: string;
}) {
  return (
    <article className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="fact">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}

function Status({ value }: { value: string }) {
  return <span className={`source-status ${statusTone(value)}`}>{value}</span>;
}

function ParsePointer({ label, job }: { label: string; job?: ParseJob }) {
  return (
    <article className="parse-pointer">
      <span>{label}</span>
      {job ? (
        <>
          <Status value={job.status} />
          <strong>{shortId(job.id)}</strong>
          <small>
            {job.parser_id}@{job.parser_version}
          </small>
          <code title={job.config_checksum}>
            config {shortHash(job.config_checksum)}
          </code>
          <small>
            document {job.document_model_version} · locator{" "}
            {job.locator_version}
          </small>
        </>
      ) : (
        <small>尚无指针</small>
      )}
    </article>
  );
}

function FailureUnits({ items }: { items: ParseJob["failure_units"] }) {
  return (
    <div className="failure-units">
      <h3>失败单元 · {items.length}</h3>
      <ol>
        {items.map((item) => (
          <li key={item.id}>
            <Status value={item.error_code} />
            <strong>
              {item.scope} / {item.scope_ref}
            </strong>
            <span>{item.safe_detail}</span>
            <small>{item.retryable ? "可重试" : "不可原样重试"}</small>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void | Promise<void>;
}) {
  return (
    <div className="form-error" role="alert">
      <span>{message}</span>
      {onRetry && <button onClick={() => void onRetry()}>重试</button>}
    </div>
  );
}

function Loading({ text }: { text: string }) {
  return (
    <div className="source-loading" aria-live="polite">
      <i />
      <span>{text}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function FutureBoundary() {
  return (
    <section className="future-boundary" aria-label="后续阶段边界">
      <div>
        <span>M4+ BOUNDARY</span>
        <strong>自动编译与 Connector 当前不可用</strong>
        <small>
          M3 只建立 Raw、Parse、Segment 与
          SourceAnchor，不生成知识或连接外部系统。
        </small>
      </div>
      <button disabled>解析后自动编译</button>
      <button disabled>管理 Connector</button>
    </section>
  );
}

function readSourceRoute(pathname: string): SourceRoute {
  if (pathname === "/sources" || pathname === "/sources/")
    return { kind: "list" };
  let match = pathname.match(/^\/sources\/([^/]+)\/versions\/([^/]+)\/?$/);
  if (match)
    return { kind: "version", sourceId: match[1], versionId: match[2] };
  match = pathname.match(/^\/sources\/([^/]+)\/?$/);
  if (match) return { kind: "source", sourceId: match[1] };
  match = pathname.match(/^\/source-versions\/([^/]+)\/preview\/?$/);
  if (match) return { kind: "preview", versionId: match[1] };
  return { kind: "unknown" };
}

function readSourceFilters(path: string): SourceFilters {
  const query = new URL(path, location.origin).searchParams;
  return {
    search: query.get("search") ?? "",
    type: query.get("type") ?? "",
    status: query.get("status") ?? "",
    classification: query.get("classification") ?? "",
    cursor: query.get("cursor") ?? "",
  };
}

function hasFilters(filters: SourceFilters) {
  return Boolean(
    filters.search || filters.type || filters.status || filters.classification,
  );
}

function canManageSources(principal: Principal) {
  return principal.roles.some((role) =>
    [
      "platform_admin",
      "tenant_admin",
      "space_admin",
      "knowledge_engineer",
    ].includes(role),
  );
}

async function sha256(file: File) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    await file.arrayBuffer(),
  );
  return `sha256:${Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")}`;
}

function latestVersion(versions: SourceVersion[]) {
  return [...versions].sort(
    (left, right) =>
      new Date(right.created_at).getTime() -
      new Date(left.created_at).getTime(),
  )[0];
}

function sourceName(filename: string) {
  return (
    filename.replace(/\.[^.]+$/, "").slice(0, 255) || filename.slice(0, 255)
  );
}

function splitTags(value: string) {
  return [
    ...new Set(
      value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ].slice(0, 64);
}

function inferContentType(filename: string) {
  const extension = filename.split(".").pop()?.toLowerCase();
  return (
    {
      pdf: "application/pdf",
      docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      md: "text/markdown",
      markdown: "text/markdown",
      txt: "text/plain",
      csv: "text/csv",
      xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }[extension ?? ""] ?? "application/octet-stream"
  );
}

function batchStageLabel(status: string) {
  return (
    {
      UPLOADING: "正在上传 Raw",
      PROCESSING: "已登记，解析执行中",
      SUCCEEDED: "解析成功",
      PARTIAL: "部分解析；请查看失败单元",
      FAILED: "导入或解析失败",
      CANCELED: "已取消",
    }[status] ?? status
  );
}

function outcomesFromBatch(batch: ImportBatch): UploadOutcome[] {
  return batch.items.map((item) => ({
    filename: item.filename,
    stage: item.status,
    detail: item.safe_detail || batchStageLabel(item.status),
  }));
}

function statusTone(value: string) {
  if (
    [
      "FAILED",
      "PARTIAL",
      "PARTIAL_FAILED",
      "OCR_REQUIRED",
      "UNRESOLVED",
      "REVOKED",
    ].includes(value)
  )
    return "danger";
  if (
    [
      "PARSING",
      "QUEUED",
      "RUNNING",
      "PROCESSING",
      "STALE",
      "CHECKSUM",
    ].includes(value)
  )
    return "warning";
  if (["SUCCEEDED", "PARSED", "ACTIVE", "VALID", "STORED"].includes(value))
    return "success";
  return "neutral";
}

function locatorLabel(locator: Locator) {
  if (locator.kind === "page") return `page ${locator.page}`;
  if (locator.kind === "block") return `block ${locator.block_id}`;
  if (locator.kind === "character_range")
    return `chars ${locator.start}–${locator.end} (${locator.text_basis})`;
  if (locator.kind === "table_cell")
    return `table ${locator.table_id} · r${locator.row_start}:${locator.row_end} c${locator.column_start}:${locator.column_end}`;
  if (locator.kind === "bounding_box")
    return `page ${locator.page} · bbox ${locator.x}, ${locator.y}, ${locator.width} × ${locator.height}`;
  return `time ${locator.start_ms}–${locator.end_ms}ms`;
}

function anchorExplanation(status?: AnchorStatus | null) {
  if (!status) return "未指定 Anchor，展示当前 active ParseJob 的净化内容。";
  const explanations: Record<AnchorStatus, string> = {
    VALID: "所有必需绑定仍可在固定 SourceVersion 与 ParseJob 中验证。",
    STALE: "旧定位已无法在原解析结果中完整验证；历史绑定仍被保留。",
    UNRESOLVED: "系统无法安全定位该 Anchor，未使用全文猜测替代。",
    REVOKED: "资料已失效或访问被撤销，正文展示受限。",
  };
  return explanations[status];
}

function segmentPosition(segment: DocumentSegment) {
  if (segment.sheet_name)
    return `${segment.sheet_name} · row ${segment.row_index ?? "-"} · col ${segment.column_index ?? "-"}`;
  if (segment.page_number) return `page ${segment.page_number}`;
  return segment.structure_path;
}

function shortId(value: string) {
  return value.length > 13 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function shortHash(value: string) {
  return value.length > 20 ? `${value.slice(0, 15)}…${value.slice(-6)}` : value;
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string | Date) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function messageOf(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "资料中心发生未知错误，请重试。";
}
