export type Principal = {
  actor_type: "USER" | "SERVICE";
  actor_id: string;
  tenant_id: string;
  subject: string;
  roles: string[];
  clearance: string;
};

export type KnowledgeSpace = {
  id: string;
  tenant_id: string;
  organization_id: string;
  slug: string;
  display_name: string;
  description: string;
  default_classification: string;
  status: "ACTIVE" | "ARCHIVED";
  version: number;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  archived_at?: string;
};

export type WorkflowType =
  | "SOURCE_INGESTION"
  | "KNOWLEDGE_COMPILE"
  | "HUMAN_REVIEW"
  | "QUALITY_EVALUATION"
  | "KNOWLEDGE_RELEASE"
  | "DOMAIN_PACK_INSTALL"
  | "GRIDCREW_FEEDBACK_INGESTION";

export type WorkflowTask = {
  id: string;
  tenant_id: string;
  space_id: string;
  workflow_type: WorkflowType;
  business_key: string;
  display_name: string;
  workflow_id: string;
  temporal_run_id?: string;
  status: string;
  version: number;
  progress: number;
  current_step?: string;
  input_refs: Record<string, string>;
  result_summary: Record<string, unknown>;
  projection_revision: number;
  projection_in_sync: boolean;
  created_at: string;
  updated_at: string;
};

export type DataClassification =
  | "PUBLIC"
  | "INTERNAL"
  | "CONFIDENTIAL"
  | "HIGHLY_RESTRICTED";

export type SourceVersion = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_document_id: string;
  filename: string;
  content_type: string;
  size: number;
  checksum: string;
  object_version_id?: string;
  classification: DataClassification;
  status: "STORED" | "PARSING" | "PARTIAL" | "PARSED" | "FAILED" | "SUPERSEDED";
  version: number;
  active_parse_job_id?: string;
  latest_parse_job_id?: string;
  supersedes_source_version_id?: string;
  created_at: string;
  created_by: string;
};

export type SourceDocument = {
  id: string;
  tenant_id: string;
  space_id: string;
  display_name: string;
  description: string;
  classification: DataClassification;
  source_level?: string;
  tags: string[];
  valid_until?: string;
  status: "REGISTERED" | "ACTIVE" | "ARCHIVED";
  version: number;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  versions: SourceVersion[];
};

export type SourceUploadCreate = {
  filename: string;
  content_type: string;
  expected_size: number;
  expected_checksum: string;
  display_name: string;
  description?: string;
  classification: DataClassification;
  source_level?: string;
  tags?: string[];
  valid_until?: string;
  source_document_id?: string;
  supersedes_source_version_id?: string;
  import_batch_id?: string;
};

export type SourceUploadSession = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_document_id: string;
  source_version_id: string;
  import_batch_id?: string;
  filename: string;
  content_type: string;
  expected_size: number;
  expected_checksum: string;
  object_key: string;
  status:
    | "INITIATED"
    | "UPLOADING"
    | "COMPLETING"
    | "COMPLETED"
    | "ABORTED"
    | "EXPIRED";
  version: number;
  upload_url: string;
  expires_at: string;
  created_at: string;
};

export type ParseFailureUnit = {
  id: string;
  parse_job_id: string;
  error_code: string;
  scope: string;
  scope_ref: string;
  retryable: boolean;
  safe_detail: string;
};

export type ParseJob = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_version_id: string;
  status:
    | "CREATED"
    | "QUEUED"
    | "RUNNING"
    | "PARTIAL_FAILED"
    | "FAILED"
    | "SUCCEEDED"
    | "CANCELED";
  version: number;
  parser_id: string;
  parser_version: string;
  config_checksum: string;
  document_model_version: string;
  locator_version: string;
  ocr_provider_id?: string;
  ocr_provider_version?: string;
  workflow_id: string;
  temporal_run_id?: string;
  result_checksum?: string;
  failure_units: ParseFailureUnit[];
  created_at: string;
  updated_at: string;
};

export type ImportBatch = {
  id: string;
  tenant_id: string;
  space_id: string;
  display_name: string;
  status:
    | "CREATED"
    | "UPLOADING"
    | "PROCESSING"
    | "PARTIAL"
    | "SUCCEEDED"
    | "FAILED"
    | "CANCELED";
  version: number;
  item_summary: Record<string, number>;
  items: Array<Record<string, unknown>>;
  created_at: string;
  created_by: string;
};

export type DocumentSegment = {
  id: string;
  source_version_id: string;
  parse_job_id: string;
  sequence: number;
  block_type: string;
  structure_path: string;
  normalized_text?: string;
  derived_object_key?: string;
  text_checksum: string;
  locators: Array<Record<string, unknown>>;
  parser_id: string;
  parser_version: string;
  config_checksum: string;
  document_model_version: string;
  locator_version: string;
};

export type SourcePreview = {
  source_version_id: string;
  parse_job_id: string;
  anchor_id?: string;
  anchor_status?: "VALID" | "STALE" | "UNRESOLVED" | "REVOKED";
  content_type: "text/plain" | "text/html";
  sanitized_content: string;
  locator_results: Array<Record<string, unknown>>;
};

export class NexweaveSdkError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly traceId?: string,
  ) {
    super(message);
  }
}

export class NexweaveClient {
  constructor(
    private readonly baseUrl: string,
    private readonly accessToken: string,
  ) {}

  me() {
    return this.request<Principal>("GET", "/api/v1/auth/me");
  }

  listSpaces() {
    return this.request<{ items: KnowledgeSpace[] }>("GET", "/api/v1/spaces");
  }

  createSpace(body: Record<string, unknown>, idempotencyKey: string) {
    return this.request<KnowledgeSpace>("POST", "/api/v1/spaces", body, {
      "Idempotency-Key": idempotencyKey,
    });
  }

  updateSpace(
    spaceId: string,
    body: Record<string, unknown>,
    version: number,
    idempotencyKey: string,
  ) {
    return this.request<KnowledgeSpace>(
      "PATCH",
      `/api/v1/spaces/${spaceId}`,
      body,
      {
        "Idempotency-Key": idempotencyKey,
        "If-Match": `"v${version}"`,
      },
    );
  }

  archiveSpace(spaceId: string, version: number, idempotencyKey: string) {
    return this.request<KnowledgeSpace>(
      "POST",
      `/api/v1/spaces/${spaceId}/archive`,
      undefined,
      { "Idempotency-Key": idempotencyKey, "If-Match": `"v${version}"` },
    );
  }

  listWorkflowTasks(spaceId: string) {
    return this.request<{ items: WorkflowTask[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/workflow-tasks`,
    );
  }

  getWorkflowTask(taskId: string) {
    return this.request<{
      task: WorkflowTask;
      steps: Array<Record<string, unknown>>;
      events: Array<Record<string, unknown>>;
      allowed_actions: string[];
    }>("GET", `/api/v1/workflow-tasks/${taskId}`);
  }

  createWorkflowTask(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<WorkflowTask>(
      "POST",
      `/api/v1/spaces/${spaceId}/workflow-tasks`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  commandWorkflowTask(
    taskId: string,
    body: Record<string, unknown>,
    version: number,
    idempotencyKey: string,
  ) {
    return this.request<{ task: WorkflowTask; command_id: string }>(
      "POST",
      `/api/v1/workflow-tasks/${taskId}/commands`,
      body,
      {
        "Idempotency-Key": idempotencyKey,
        "If-Match": `"v${version}"`,
      },
    );
  }

  reconcileWorkflowTask(taskId: string) {
    return this.request<{
      task: WorkflowTask;
      repaired: boolean;
      temporal_status: string;
    }>("POST", `/api/v1/workflow-tasks/${taskId}/reconcile`);
  }

  createSourceImportBatch(
    spaceId: string,
    displayName: string,
    idempotencyKey: string,
  ) {
    return this.request<ImportBatch>(
      "POST",
      `/api/v1/spaces/${spaceId}/source-import-batches`,
      { display_name: displayName },
      { "Idempotency-Key": idempotencyKey },
    );
  }

  getSourceImportBatch(batchId: string) {
    return this.request<ImportBatch>(
      "GET",
      `/api/v1/source-import-batches/${batchId}`,
    );
  }

  createSourceUpload(
    spaceId: string,
    body: SourceUploadCreate,
    idempotencyKey: string,
  ) {
    return this.request<SourceUploadSession>(
      "POST",
      `/api/v1/spaces/${spaceId}/sources/uploads`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  uploadSourceContent(
    uploadId: string,
    content: ArrayBuffer,
    contentType: string,
  ) {
    return this.request<SourceUploadSession>(
      "PUT",
      `/api/v1/sources/uploads/${uploadId}/content`,
      content,
      { "Content-Type": contentType },
    );
  }

  completeSourceUpload(
    uploadId: string,
    body: { checksum: string; size: number },
    idempotencyKey: string,
  ) {
    return this.request<{
      source_id: string;
      source_version_id: string;
      parse_job_id: string;
      workflow_id: string;
      run_id?: string;
    }>("POST", `/api/v1/sources/uploads/${uploadId}/complete`, body, {
      "Idempotency-Key": idempotencyKey,
    });
  }

  listSources(
    spaceId: string,
    filters: {
      limit?: number;
      cursor?: string;
      status?: string;
      content_type?: string;
      classification?: DataClassification;
      search?: string;
    } = {},
  ) {
    return this.request<{ items: SourceDocument[]; next_cursor?: string }>(
      "GET",
      this.withQuery(`/api/v1/spaces/${spaceId}/sources`, filters),
    );
  }

  getSource(sourceId: string) {
    return this.request<SourceDocument>("GET", `/api/v1/sources/${sourceId}`);
  }

  archiveSource(sourceId: string, version: number, idempotencyKey: string) {
    return this.request<SourceDocument>(
      "POST",
      `/api/v1/sources/${sourceId}/archive`,
      undefined,
      { "Idempotency-Key": idempotencyKey, "If-Match": `"v${version}"` },
    );
  }

  getSourceVersion(sourceId: string, versionId: string) {
    return this.request<SourceVersion>(
      "GET",
      `/api/v1/sources/${sourceId}/versions/${versionId}`,
    );
  }

  downloadSourceVersion(versionId: string) {
    return this.request<ArrayBuffer>(
      "GET",
      `/api/v1/source-versions/${versionId}/content`,
      undefined,
      {},
      "arrayBuffer",
    );
  }

  reparseSourceVersion(
    versionId: string,
    body: Record<string, unknown>,
    version: number,
    idempotencyKey: string,
  ) {
    return this.request<ParseJob>(
      "POST",
      `/api/v1/source-versions/${versionId}/parse`,
      body,
      {
        "Idempotency-Key": idempotencyKey,
        "If-Match": `"v${version}"`,
      },
    );
  }

  retryParseJob(parseJobId: string, version: number, idempotencyKey: string) {
    return this.request<ParseJob>(
      "POST",
      `/api/v1/parse-jobs/${parseJobId}/retry`,
      undefined,
      { "Idempotency-Key": idempotencyKey, "If-Match": `"v${version}"` },
    );
  }

  cancelParseJob(parseJobId: string, version: number, idempotencyKey: string) {
    return this.request<ParseJob>(
      "POST",
      `/api/v1/parse-jobs/${parseJobId}/cancel`,
      undefined,
      { "Idempotency-Key": idempotencyKey, "If-Match": `"v${version}"` },
    );
  }

  getParseJob(parseJobId: string) {
    return this.request<ParseJob>("GET", `/api/v1/parse-jobs/${parseJobId}`);
  }

  listSourceSegments(
    versionId: string,
    filters: { limit?: number; cursor?: string; parse_job_id?: string } = {},
  ) {
    return this.request<{ items: DocumentSegment[]; next_cursor?: string }>(
      "GET",
      this.withQuery(`/api/v1/source-versions/${versionId}/segments`, filters),
    );
  }

  previewSourceVersion(versionId: string, anchorId?: string) {
    return this.request<SourcePreview>(
      "GET",
      this.withQuery(`/api/v1/source-versions/${versionId}/preview`, {
        anchor_id: anchorId,
      }),
    );
  }

  invalidateSourceVersion(
    versionId: string,
    body: { reason_code: string; reason: string; policy_version: string },
    version: number,
    idempotencyKey: string,
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/api/v1/source-versions/${versionId}/invalidate`,
      body,
      { "Idempotency-Key": idempotencyKey, "If-Match": `"v${version}"` },
    );
  }

  private withQuery(
    path: string,
    values: Record<string, string | number | undefined>,
  ) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if (value !== undefined) query.set(key, String(value));
    }
    const rendered = query.toString();
    return rendered ? `${path}?${rendered}` : path;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: Record<string, unknown> | BodyInit,
    extraHeaders: Record<string, string> = {},
    responseType: "json" | "arrayBuffer" = "json",
  ): Promise<T> {
    const traceId = crypto.randomUUID().replaceAll("-", "");
    const spanId = crypto.randomUUID().replaceAll("-", "").slice(0, 16);
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${this.accessToken}`,
        "Content-Type": "application/json",
        traceparent: `00-${traceId}-${spanId}-01`,
        ...extraHeaders,
      },
      body:
        body === undefined
          ? undefined
          : this.isJsonBody(body)
            ? JSON.stringify(body)
            : body,
    });
    if (!response.ok) {
      const problem = (await response.json()) as {
        code?: string;
        detail?: string;
        trace_id?: string;
      };
      throw new NexweaveSdkError(
        response.status,
        problem.code ?? "API_ERROR",
        problem.detail ?? "The API request failed.",
        problem.trace_id ?? response.headers.get("X-Trace-Id") ?? undefined,
      );
    }
    return (
      responseType === "arrayBuffer"
        ? await response.arrayBuffer()
        : await response.json()
    ) as T;
  }

  private isJsonBody(
    body: Record<string, unknown> | BodyInit,
  ): body is Record<string, unknown> {
    return (
      typeof body === "object" &&
      !(body instanceof Blob) &&
      !(body instanceof ArrayBuffer) &&
      !ArrayBuffer.isView(body) &&
      !(body instanceof FormData) &&
      !(body instanceof URLSearchParams) &&
      !(body instanceof ReadableStream)
    );
  }
}
