import type {
  SignalBinding,
  ForecastRun,
  BindingInput,
  BindingValidation,
  BindingEntity,
  CsvBindingPreview,
  ForecastRuntime,
  ForecastRequest,
  ForecastArtifact,
  ForecastKnowledgeContext,
} from "./livingTypes";
import type {
  AuditLog,
  CompileJob,
  GovernanceObject,
  Member,
  Organization,
  Principal,
  RoleDescriptor,
  Session,
  Space,
  CursorPage,
  DocumentSegment,
  ImportBatch,
  ParseJob,
  PreviewResponse,
  SourceDocument,
  SourceFilters,
  SourceUploadComplete,
  SourceUploadSession,
  SourceVersion,
  SchemaVersion,
  CompositionReport,
  DomainPackInstallation,
  DomainPackVersion,
  User,
  WorkflowCommand,
  WorkflowTask,
  WorkflowTaskDetail,
  WikiPage,
  WikiLinkGraph,
  WikiPageVersion,
  Claim,
  ConflictCase,
  ReviewCase,
  EvaluationSuite,
  GraphTraverse,
  KnowledgeRelease,
  QueryAnswer,
  ReleaseCandidate,
  ConnectorInstance,
  ConnectorSyncRun,
} from "./types";

type ListResponse<T> = { items: T[] };

export class ApiError extends Error {
  readonly rawMessage: string;
  readonly kind: AppErrorKind;

  constructor(
    rawMessage: string,
    readonly status: number,
    readonly code?: string,
    readonly requestId?: string,
  ) {
    const kind = classifyError(status, code);
    super(ERROR_MESSAGES[kind]);
    this.name = "ApiError";
    this.kind = kind;
    this.rawMessage = rawMessage;
    if (isDeveloperEnvironment()) {
      console.warn("NEXWEAVE API request failed", {
        kind,
        code,
        status,
        requestId,
        rawMessage,
      });
    }
  }
}

export type AppErrorKind =
  | "ACCESS_DENIED"
  | "NOT_FOUND"
  | "PRECONDITION_FAILED"
  | "VALIDATION_ERROR"
  | "CONFLICT"
  | "NETWORK_ERROR"
  | "SERVER_ERROR"
  | "UNKNOWN";

const ERROR_MESSAGES: Record<AppErrorKind, string> = {
  ACCESS_DENIED: "当前账号没有执行此操作的权限。",
  NOT_FOUND: "请求的内容不存在，或已不再可用。",
  PRECONDITION_FAILED: "当前操作缺少必要的前置条件。",
  VALIDATION_ERROR: "提交的信息不完整或格式不正确，请检查后重试。",
  CONFLICT: "内容已发生变化，请刷新后再试。",
  NETWORK_ERROR: "暂时无法连接服务，请稍后重试。",
  SERVER_ERROR: "服务暂时不可用，请稍后重试。",
  UNKNOWN: "操作未能完成，请稍后重试。",
};

function classifyError(status: number, code?: string): AppErrorKind {
  const normalized = (code ?? "").toUpperCase();
  if (status === 401 || status === 403 || /DENIED|FORBIDDEN/.test(normalized))
    return "ACCESS_DENIED";
  if (status === 404 || normalized.includes("NOT_FOUND")) return "NOT_FOUND";
  if (status === 412 || status === 428 || normalized.includes("PRECONDITION"))
    return "PRECONDITION_FAILED";
  if (status === 409 || normalized.includes("CONFLICT")) return "CONFLICT";
  if (status === 400 || status === 422 || normalized.includes("VALIDATION"))
    return "VALIDATION_ERROR";
  if (status >= 500) return "SERVER_ERROR";
  return "UNKNOWN";
}

export function messageOf(error: unknown, fallback?: string) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return ERROR_MESSAGES.NETWORK_ERROR;
  if (isDeveloperEnvironment() && error instanceof Error)
    console.warn("NEXWEAVE UI operation failed", error);
  return fallback ?? ERROR_MESSAGES.UNKNOWN;
}

export function isDeveloperEnvironment() {
  if (typeof location === "undefined") return false;
  return ["localhost", "127.0.0.1", "::1"].includes(location.hostname);
}

export class NexweaveApi {
  constructor(private readonly token?: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    const traceId = crypto.randomUUID().replaceAll("-", "");
    const spanId = crypto.randomUUID().replaceAll("-", "").slice(0, 16);
    headers.set("Accept", "application/json");
    headers.set("traceparent", `00-${traceId}-${spanId}-01`);
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    if (init.body && !headers.has("Content-Type"))
      headers.set("Content-Type", "application/json");
    const response = await fetch(`/api/v1${path}`, { ...init, headers });
    if (!response.ok) {
      const problem = (await response.json().catch(() => ({}))) as {
        detail?: string;
        code?: string;
        request_id?: string;
      };
      throw new ApiError(
        problem.detail || `请求失败（${response.status}）`,
        response.status,
        problem.code,
        problem.request_id ?? response.headers.get("x-request-id") ?? undefined,
      );
    }
    return (await response.json()) as T;
  }

  bindingEntities(spaceId: string) {
    return this.request<{ items: BindingEntity[] }>(
      `/spaces/${spaceId}/binding-entities`,
    );
  }
  csvBindingPreview(spaceId: string, id: string) {
    return this.request<CsvBindingPreview>(
      `/spaces/${spaceId}/time-series-sources/${id}/preview`,
    );
  }
  validateBinding(spaceId: string, body: BindingInput) {
    return this.request<BindingValidation>(
      `/spaces/${spaceId}/signal-bindings/validate`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
  }
  createBinding(spaceId: string, body: BindingInput, key: string) {
    return this.request<SignalBinding>(`/spaces/${spaceId}/signal-bindings`, {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify(body),
    });
  }
  signalBindings(spaceId: string) {
    return this.request<{ items: SignalBinding[] }>(
      `/spaces/${spaceId}/signal-bindings`,
    );
  }
  forecastRuns(spaceId: string) {
    return this.request<{ items: ForecastRun[] }>(
      `/spaces/${spaceId}/forecast-runs`,
    );
  }
  forecastRuntime(spaceId: string) {
    return this.request<ForecastRuntime>(`/spaces/${spaceId}/forecast-runtime`);
  }
  forecastCommand(
    id: string,
    action: "cancel" | "retry",
    reason: string,
    key: string,
  ) {
    return this.request<ForecastRun>(`/forecast-runs/${id}/${action}`, {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify({ reason }),
    });
  }
  forecastRun(id: string) {
    return this.request<ForecastRun>(`/forecast-runs/${id}`);
  }
  forecastArtifact(id: string) {
    return this.request<ForecastArtifact>(`/forecast-artifacts/${id}`);
  }
  createForecast(spaceId: string, body: ForecastRequest, key: string) {
    return this.request<ForecastRun>(`/spaces/${spaceId}/forecast-runs`, {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify(body),
    });
  }

  login(subject: string) {
    return this.request<Session>("/auth/dev/session", {
      method: "POST",
      body: JSON.stringify({ subject }),
    });
  }

  me() {
    return this.request<Principal>("/auth/me");
  }

  organizations() {
    return this.request<ListResponse<Organization>>("/organizations");
  }

  async spaces(): Promise<ListResponse<Space>> {
    const items: Space[] = [];
    let cursor: string | null = null;
    const seen = new Set<string>();
    do {
      const page: ListResponse<Space> & { next_cursor?: string | null } =
        await this.request(
          cursor ? `/spaces?cursor=${encodeURIComponent(cursor)}` : "/spaces",
        );
      items.push(...page.items);
      cursor = page.next_cursor ?? null;
      if (cursor && seen.has(cursor))
        throw new Error("Space pagination repeated a cursor.");
      if (cursor) seen.add(cursor);
    } while (cursor);
    return { items };
  }

  createSpace(body: Record<string, unknown>) {
    return this.request<Space>("/spaces", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  connectorInstances(spaceId: string) {
    return this.request<ListResponse<ConnectorInstance>>(
      `/spaces/${spaceId}/connector-instances`,
    );
  }

  createConnectorInstance(spaceId: string, body: Record<string, unknown>) {
    return this.request<ConnectorInstance>(
      `/spaces/${spaceId}/connector-instances`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  startConnectorSync(spaceId: string, instanceId: string) {
    return this.request<ConnectorSyncRun>(
      `/spaces/${spaceId}/connector-instances/${instanceId}/sync-runs`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ requested_watermark: {} }),
      },
    );
  }

  updateSpace(space: Space, body: Record<string, unknown>) {
    return this.request<Space>(`/spaces/${space.id}`, {
      method: "PATCH",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${space.version}"`,
      },
      body: JSON.stringify(body),
    });
  }

  archiveSpace(space: Space) {
    return this.request<Space>(`/spaces/${space.id}/archive`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${space.version}"`,
      },
    });
  }

  members(spaceId: string) {
    return this.request<ListResponse<Member>>(`/spaces/${spaceId}/members`);
  }

  grantMember(
    spaceId: string,
    subjectId: string,
    body: Record<string, unknown>,
  ) {
    return this.request<Member>(`/spaces/${spaceId}/members/${subjectId}`, {
      method: "PUT",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  revokeMember(spaceId: string, subjectId: string) {
    return this.request<Member>(`/spaces/${spaceId}/members/${subjectId}`, {
      method: "DELETE",
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
  }

  users() {
    return this.request<ListResponse<User>>("/users");
  }

  createUser(body: Record<string, unknown>) {
    return this.request<User>("/users", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  roles() {
    return this.request<ListResponse<RoleDescriptor>>("/roles");
  }

  audits() {
    return this.request<ListResponse<AuditLog>>("/audit-logs?limit=50");
  }

  listGovernance(
    kind: "model-profiles" | "prompt-versions" | "connector-definitions",
  ) {
    return this.request<ListResponse<GovernanceObject>>(`/${kind}`);
  }

  createGovernance(
    kind: "model-profiles" | "prompt-versions" | "connector-definitions",
    body: Record<string, unknown>,
  ) {
    return this.request<GovernanceObject>(`/${kind}`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  workflowTasks(spaceId: string) {
    return this.request<ListResponse<WorkflowTask>>(
      `/spaces/${spaceId}/workflow-tasks`,
    );
  }

  workflowTask(taskId: string) {
    return this.request<WorkflowTaskDetail>(`/workflow-tasks/${taskId}`);
  }

  createWorkflowTask(spaceId: string, body: Record<string, unknown>) {
    return this.request<WorkflowTask>(`/spaces/${spaceId}/workflow-tasks`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  commandWorkflowTask(
    task: WorkflowTask,
    action: WorkflowCommand,
    reason = "",
  ) {
    return this.request<{ task: WorkflowTask; command_id: string }>(
      `/workflow-tasks/${task.id}/commands`,
      {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "If-Match": `"v${task.version}"`,
        },
        body: JSON.stringify({ action, reason }),
      },
    );
  }

  reconcileWorkflowTask(taskId: string) {
    return this.request<{
      task: WorkflowTask;
      repaired: boolean;
      temporal_status: string;
    }>(`/workflow-tasks/${taskId}/reconcile`, { method: "POST" });
  }

  schemas(spaceId: string) {
    return this.request<ListResponse<SchemaVersion>>(
      `/spaces/${spaceId}/schemas`,
    );
  }

  createSchema(spaceId: string, body: Record<string, unknown>) {
    return this.request<SchemaVersion>(`/spaces/${spaceId}/schemas`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  validateSchema(schema: SchemaVersion) {
    return this.request<CompositionReport>(
      `/schemas/${schema.schema_definition_id}/versions/${encodeURIComponent(schema.semantic_version)}/validate`,
      { method: "POST" },
    );
  }

  publishSchema(schema: SchemaVersion) {
    return this.request<SchemaVersion>(
      `/schemas/${schema.schema_definition_id}/versions/${encodeURIComponent(schema.semantic_version)}/publish`,
      {
        method: "POST",
        headers: {
          "If-Match": `"v${schema.version}"`,
          "Idempotency-Key": crypto.randomUUID(),
        },
      },
    );
  }

  domainPacks() {
    return this.request<ListResponse<DomainPackVersion>>("/domain-packs");
  }

  installDomainPack(
    spaceId: string,
    body: {
      domain_pack_version_id: string;
      schema_definition_id: string;
      semantic_version: string;
      operation?: "INSTALL" | "UPGRADE";
      previous_installation_id?: string;
    },
  ) {
    return this.request<DomainPackInstallation>(
      `/spaces/${spaceId}/domain-pack-installations`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  domainPackInstallation(id: string) {
    return this.request<DomainPackInstallation>(
      `/domain-pack-installations/${id}`,
    );
  }

  disableDomainPack(spaceId: string, id: string) {
    return this.request<DomainPackInstallation>(
      `/spaces/${spaceId}/domain-pack-installations/${id}/disable`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      },
    );
  }

  rollbackDomainPack(spaceId: string, targetInstallationId: string) {
    return this.request<DomainPackInstallation>(
      `/spaces/${spaceId}/domain-pack-installations/rollback`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ target_installation_id: targetInstallationId }),
      },
    );
  }

  sources(spaceId: string, filters: SourceFilters = {}) {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "")
        query.set(key === "type" ? "content_type" : key, String(value));
    });
    const suffix = query.size ? `?${query}` : "";
    return this.request<CursorPage<SourceDocument>>(
      `/spaces/${spaceId}/sources${suffix}`,
    );
  }

  source(sourceId: string) {
    return this.request<SourceDocument>(`/sources/${sourceId}`);
  }

  sourceVersion(sourceId: string, versionId: string) {
    return this.request<SourceVersion>(
      `/sources/${sourceId}/versions/${versionId}`,
    );
  }

  parseJob(parseJobId: string) {
    return this.request<ParseJob>(`/parse-jobs/${parseJobId}`);
  }

  sourceSegments(
    versionId: string,
    options: { parse_job_id?: string; cursor?: string; limit?: number } = {},
  ) {
    const query = new URLSearchParams();
    Object.entries(options).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    const suffix = query.size ? `?${query}` : "";
    return this.request<CursorPage<DocumentSegment>>(
      `/source-versions/${versionId}/segments${suffix}`,
    );
  }

  sourcePreview(versionId: string, anchorId?: string) {
    const query = anchorId
      ? `?${new URLSearchParams({ anchor_id: anchorId })}`
      : "";
    return this.request<PreviewResponse>(
      `/source-versions/${versionId}/preview${query}`,
    );
  }

  createImportBatch(spaceId: string, displayName: string) {
    return this.request<ImportBatch>(
      `/spaces/${spaceId}/source-import-batches`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ display_name: displayName }),
      },
    );
  }

  importBatch(batchId: string) {
    return this.request<ImportBatch>(`/source-import-batches/${batchId}`);
  }

  createSourceUpload(spaceId: string, body: Record<string, unknown>) {
    return this.request<SourceUploadSession>(
      `/spaces/${spaceId}/sources/uploads`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  async uploadSourceContent(
    session: SourceUploadSession,
    file: File,
    signal?: AbortSignal,
  ) {
    const headers = new Headers({
      Accept: "application/json",
      "Content-Type": file.type || "application/octet-stream",
    });
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    const target = new URL(session.upload_url, location.origin);
    const expectedPath = `/api/v1/sources/uploads/${session.id}/content`;
    if (target.origin !== location.origin || target.pathname !== expectedPath) {
      throw new ApiError(
        "上传端点不受信任。",
        400,
        "SOURCE_UPLOAD_URL_INVALID",
      );
    }
    const response = await fetch(target.pathname + target.search, {
      method: "PUT",
      headers,
      body: file,
      signal,
    });
    if (!response.ok) await this.throwProblem(response);
  }

  completeSourceUpload(uploadId: string, checksum: string, size: number) {
    return this.request<SourceUploadComplete>(
      `/sources/uploads/${uploadId}/complete`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ checksum, size }),
      },
    );
  }

  abortSourceUpload(uploadId: string) {
    return this.request<SourceUploadSession>(
      `/sources/uploads/${uploadId}/abort`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      },
    );
  }

  archiveSource(source: SourceDocument) {
    return this.request<SourceDocument>(`/sources/${source.id}/archive`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${source.version}"`,
      },
    });
  }

  reparseSourceVersion(version: SourceVersion, body: Record<string, unknown>) {
    return this.request<ParseJob>(`/source-versions/${version.id}/parse`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${version.version}"`,
      },
      body: JSON.stringify(body),
    });
  }

  retryParseJob(job: ParseJob) {
    return this.request<ParseJob>(`/parse-jobs/${job.id}/retry`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${job.version}"`,
      },
    });
  }

  cancelParseJob(job: ParseJob) {
    return this.request<ParseJob>(`/parse-jobs/${job.id}/cancel`, {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"v${job.version}"`,
      },
    });
  }

  compileJobs(spaceId: string) {
    return this.request<ListResponse<CompileJob>>(
      `/spaces/${spaceId}/compile-jobs`,
    );
  }

  compileJob(jobId: string) {
    return this.request<CompileJob>(`/compile-jobs/${jobId}`);
  }

  createCompileJob(
    spaceId: string,
    body: {
      schema_version_id: string;
      source_version_ids: string[];
      prompt_version_id: string;
      model_profile_id: string;
      mode: CompileJob["mode"];
      scope?: Record<string, unknown>;
    },
  ) {
    return this.request<CompileJob>(`/spaces/${spaceId}/compile-jobs`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  wikiPages(spaceId: string) {
    return this.request<ListResponse<WikiPage>>(
      `/spaces/${spaceId}/wiki/pages`,
    );
  }

  wikiLinkGraph(
    spaceId: string,
    focusPageId?: string,
    maxDepth = 2,
    nodeLimit = 180,
  ) {
    const query = new URLSearchParams({
      max_depth: String(maxDepth),
      node_limit: String(nodeLimit),
    });
    if (focusPageId) query.set("focus_page_id", focusPageId);
    return this.request<WikiLinkGraph>(
      `/spaces/${spaceId}/wiki-link-graph?${query}`,
    );
  }

  wikiPage(pageId: string) {
    return this.request<WikiPage>(`/wiki/pages/${pageId}`);
  }

  wikiPageVersions(pageId: string) {
    return this.request<ListResponse<WikiPageVersion>>(
      `/wiki/pages/${pageId}/versions`,
    );
  }

  wikiPageVersion(pageId: string, versionId: string) {
    return this.request<WikiPageVersion>(
      `/wiki/pages/${pageId}/versions/${versionId}`,
    );
  }

  editWikiPage(
    page: WikiPage,
    body: {
      protected_sections: Record<string, string>;
      properties?: Record<string, unknown>;
      title?: string;
      reason: string;
    },
  ) {
    return this.request<WikiPage>(
      `/wiki/pages/${page.id}/drafts/${page.current_version_id}`,
      {
        method: "PATCH",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "If-Match": `"v${page.version}"`,
        },
        body: JSON.stringify(body),
      },
    );
  }

  followWikiPage(pageId: string, follow: boolean) {
    return this.request<{ page_id: string; followed: boolean }>(
      `/wiki/pages/${pageId}/follow`,
      { method: follow ? "PUT" : "DELETE" },
    );
  }

  claims(spaceId: string) {
    return this.request<ListResponse<Claim>>(`/spaces/${spaceId}/claims`);
  }

  conflicts(spaceId: string) {
    return this.request<ListResponse<ConflictCase>>(
      `/spaces/${spaceId}/conflicts`,
    );
  }

  reviewCases(spaceId: string) {
    return this.request<ListResponse<ReviewCase>>(
      `/spaces/${spaceId}/review-cases`,
    );
  }

  resolveConflict(
    conflictId: string,
    body: {
      resolution: string;
      reason: string;
      conditions?: Record<string, unknown>;
    },
  ) {
    return this.request<ConflictCase>(`/conflicts/${conflictId}/decisions`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
  }

  reviewAction(
    reviewCase: ReviewCase,
    task: ReviewCase["tasks"][number],
    body: { decision: string; reason: string },
  ) {
    return this.request<ReviewCase>(
      `/review-cases/${reviewCase.id}/tasks/${task.id}/actions`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  evaluationSuites(spaceId: string) {
    return this.request<EvaluationSuite[]>(
      `/spaces/${spaceId}/evaluation-suites`,
    );
  }

  createEvaluationSuite(spaceId: string, body: Record<string, unknown>) {
    return this.request<EvaluationSuite>(
      `/spaces/${spaceId}/evaluation-suites`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  releaseCandidates(spaceId: string) {
    return this.request<ListResponse<ReleaseCandidate>>(
      `/spaces/${spaceId}/release-candidates`,
    );
  }

  createReleaseCandidate(spaceId: string, body: Record<string, unknown>) {
    return this.request<ReleaseCandidate>(
      `/spaces/${spaceId}/release-candidates`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      },
    );
  }

  publishReleaseCandidate(candidateId: string, reason: string) {
    return this.request<ReleaseCandidate>(
      `/release-candidates/${candidateId}/publish`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ reason, channel: "stable" }),
      },
    );
  }

  releases(spaceId: string) {
    return this.request<ListResponse<KnowledgeRelease>>(
      `/spaces/${spaceId}/releases`,
    );
  }

  forecastKnowledge(artifactId: string, releaseId: string, question: string) {
    return this.request<ForecastKnowledgeContext>(
      `/forecast-artifacts/${artifactId}/knowledge-context`,
      {
        method: "POST",
        body: JSON.stringify({ release_id: releaseId, question }),
      },
    );
  }

  askRelease(
    releaseId: string,
    body: {
      question: string;
      strategy: string;
      top_k: number;
      filters: Record<string, unknown>;
      client_request_id: string;
    },
  ) {
    return this.request<QueryAnswer>(`/releases/${releaseId}/queries`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  graphTraverse(releaseId: string, startEntityId: string, maxDepth: number) {
    const query = new URLSearchParams({
      start_entity_id: startEntityId,
      max_depth: String(maxDepth),
      mode: "TRAVERSE",
    });
    return this.request<GraphTraverse>(
      `/releases/${releaseId}/graph/traverse?${query}`,
    );
  }

  invalidateSourceVersion(
    version: SourceVersion,
    body: { reason_code: string; reason: string; policy_version: string },
  ) {
    return this.request<{ id: string }>(
      `/source-versions/${version.id}/invalidate`,
      {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "If-Match": `"v${version.version}"`,
        },
        body: JSON.stringify(body),
      },
    );
  }

  async downloadSourceVersion(versionId: string) {
    const headers = new Headers({ Accept: "application/octet-stream" });
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    const response = await fetch(
      `/api/v1/source-versions/${versionId}/content`,
      {
        headers,
      },
    );
    if (!response.ok) await this.throwProblem(response);
    return response.blob();
  }

  private async throwProblem(response: Response): Promise<never> {
    const problem = (await response.json().catch(() => ({}))) as {
      detail?: string;
      code?: string;
      request_id?: string;
    };
    throw new ApiError(
      problem.detail || `请求失败（${response.status}）`,
      response.status,
      problem.code,
      problem.request_id ?? response.headers.get("x-request-id") ?? undefined,
    );
  }
}
