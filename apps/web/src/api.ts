import type {
  AuditLog,
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
  User,
  WorkflowCommand,
  WorkflowTask,
  WorkflowTaskDetail,
} from "./types";

type ListResponse<T> = { items: T[] };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
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
      };
      throw new ApiError(
        problem.detail || `请求失败（${response.status}）`,
        response.status,
        problem.code,
      );
    }
    return (await response.json()) as T;
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

  spaces() {
    return this.request<ListResponse<Space>>("/spaces");
  }

  createSpace(body: Record<string, unknown>) {
    return this.request<Space>("/spaces", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(body),
    });
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
    };
    throw new ApiError(
      problem.detail || `请求失败（${response.status}）`,
      response.status,
      problem.code,
    );
  }
}
