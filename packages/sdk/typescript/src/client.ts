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
  | "CONNECTOR_SYNC"
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

export type CompileJobCreate = Record<string, unknown> & {
  schema_version_id: string;
  source_version_ids: string[];
  prompt_version_id: string;
  model_profile_id: string;
  mode?: "FULL" | "INCREMENTAL" | "SOURCE_SCOPED" | "RECOMPILE";
  scope?: Record<string, unknown>;
};

export type CompileJob = {
  id: string;
  tenant_id: string;
  space_id: string;
  schema_version_id: string;
  composition_checksum: string;
  prompt_version_id: string;
  model_profile_id: string;
  workflow_task_id: string;
  workflow_id: string;
  run_id?: string;
  mode: string;
  status: string;
  input_fingerprint: string;
  normalization_version: string;
  scope: Record<string, unknown>;
  progress: number;
  cost_summary: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_code?: string;
  error_detail?: string;
  version: number;
  created_at: string;
  updated_at: string;
  sources: Array<Record<string, unknown>>;
  steps: Array<Record<string, unknown>>;
};

export type WikiPageVersion = {
  id: string;
  wiki_page_id: string;
  compile_job_id?: string;
  revision: number;
  generated_sections: Record<string, string>;
  protected_sections: Record<string, string>;
  properties: Record<string, unknown>;
  markdown: string;
  content_checksum: string;
  status: string;
  edit_reason?: string;
  created_at: string;
  created_by: string;
};

export type WikiPage = {
  id: string;
  tenant_id: string;
  space_id: string;
  schema_version_id: string;
  primary_entity_id: string;
  template_key: string;
  slug: string;
  title: string;
  status: string;
  current_version_id?: string;
  current_version?: WikiPageVersion;
  version: number;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  evidence_candidates?: Array<Record<string, unknown>>;
  followed?: boolean;
};

export type WikiLinkGraphNode = {
  id: string;
  title: string;
  template_key: string;
  status: string;
  version: number;
  updated_at: string;
  outbound_count: number;
  backlink_count: number;
};

export type WikiLinkGraphEdge = {
  id: string;
  source_page_id: string;
  target_page_id: string;
  link_kind: string;
};

export type WikiLinkGraph = {
  space_id: string;
  focus_page_id?: string;
  max_depth: number;
  node_limit: number;
  truncated: boolean;
  nodes: WikiLinkGraphNode[];
  edges: WikiLinkGraphEdge[];
};

export type Claim = {
  id: string;
  candidate_id: string;
  schema_version_id: string;
  statement: string;
  confidence_level: string;
  status: string;
};
export type ConflictCase = {
  id: string;
  cluster_key: string;
  kind: string;
  severity: string;
  blocking: boolean;
  status: string;
};
export type ReviewTask = {
  id: string;
  stage: string;
  status: string;
  due_at: string;
  escalation_count: number;
};
export type ReviewCase = {
  id: string;
  workflow_task_id: string;
  workflow_id: string;
  target_type: string;
  target_id: string;
  risk_level: string;
  status: string;
  current_stage?: string;
  tasks: ReviewTask[];
};

export type EvaluationSuite = {
  id: string;
  schema_version_id: string;
  suite_key: string;
  version: number;
  name: string;
  minimum_pass_rate: number;
  status: string;
  cases: Array<Record<string, unknown>>;
};

export type ReleaseCandidate = {
  id: string;
  space_id: string;
  version: string;
  workflow_id: string;
  status: string;
  manifest_checksum: string;
  gate_summary: Record<string, unknown>;
  lint_findings: Array<Record<string, unknown>>;
};

export type KnowledgeRelease = {
  id: string;
  space_id: string;
  version: string;
  status: "PUBLISHED";
  manifest_checksum: string;
  schema_version_id: string;
  model_profile_id: string;
  prompt_version_id: string;
  published_at: string;
};

export type QueryAnswer = {
  id: string;
  release_id: string;
  status: "COMPLETED" | "REFUSED" | "FAILED";
  direct_answer: string;
  key_basis: string[];
  uncertainty?: string;
  citations: Array<Record<string, unknown>>;
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

export type SchemaVersion = {
  id: string;
  tenant_id: string;
  space_id: string;
  schema_definition_id: string;
  schema_key: string;
  semantic_version: string;
  status: "DRAFT" | "TESTING" | "PUBLISHED" | "DEPRECATED";
  content_checksum: string;
  composition_checksum: string;
  canonicalization_algorithm: string;
  breaking_change: boolean;
  normalized_snapshot: Record<string, unknown>;
  version: number;
};

export type DomainPackVersion = {
  id: string;
  pack_key: string;
  pack_version: string;
  publisher: string;
  key_namespace: string;
  content_checksum: string;
  status: string;
};

export type DomainPackInstallation = {
  id: string;
  space_id: string;
  domain_pack_version_id: string;
  schema_definition_id: string;
  requested_semantic_version: string;
  operation: "INSTALL" | "UPGRADE" | "DISABLE" | "ROLLBACK";
  workflow_id: string;
  run_id?: string;
  candidate_schema_version_id?: string;
  composition_report_id?: string;
  status: string;
  version: number;
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

  listSchemas(spaceId: string) {
    return this.request<{ items: SchemaVersion[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/schemas`,
    );
  }

  createSchema(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<SchemaVersion>(
      "POST",
      `/api/v1/spaces/${spaceId}/schemas`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  validateSchema(schemaId: string, semanticVersion: string) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/api/v1/schemas/${schemaId}/versions/${encodeURIComponent(semanticVersion)}/validate`,
    );
  }

  publishSchema(schema: SchemaVersion) {
    return this.request<SchemaVersion>(
      "POST",
      `/api/v1/schemas/${schema.schema_definition_id}/versions/${encodeURIComponent(schema.semantic_version)}/publish`,
      undefined,
      {
        "If-Match": `"v${schema.version}"`,
        "Idempotency-Key": crypto.randomUUID(),
      },
    );
  }

  listDomainPacks() {
    return this.request<{ items: DomainPackVersion[] }>(
      "GET",
      "/api/v1/domain-packs",
    );
  }

  installDomainPack(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<DomainPackInstallation>(
      "POST",
      `/api/v1/spaces/${spaceId}/domain-pack-installations`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  getDomainPackInstallation(installationId: string) {
    return this.request<DomainPackInstallation>(
      "GET",
      `/api/v1/domain-pack-installations/${installationId}`,
    );
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

  createCompileJob(
    spaceId: string,
    body: CompileJobCreate,
    idempotencyKey: string,
  ) {
    return this.request<CompileJob>(
      "POST",
      `/api/v1/spaces/${spaceId}/compile-jobs`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  listCompileJobs(spaceId: string) {
    return this.request<{ items: CompileJob[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/compile-jobs`,
    );
  }

  getCompileJob(compileJobId: string) {
    return this.request<CompileJob>(
      "GET",
      `/api/v1/compile-jobs/${compileJobId}`,
    );
  }

  listWikiPages(spaceId: string) {
    return this.request<{ items: WikiPage[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/wiki/pages`,
    );
  }

  getWikiLinkGraph(
    spaceId: string,
    options: {
      focusPageId?: string;
      maxDepth?: number;
      nodeLimit?: number;
    } = {},
  ) {
    return this.request<WikiLinkGraph>(
      "GET",
      this.withQuery(`/api/v1/spaces/${spaceId}/wiki-link-graph`, {
        focus_page_id: options.focusPageId,
        max_depth: options.maxDepth ?? 2,
        node_limit: options.nodeLimit ?? 180,
      }),
    );
  }

  getWikiPage(pageId: string) {
    return this.request<WikiPage>("GET", `/api/v1/wiki/pages/${pageId}`);
  }

  editWikiPage(
    pageId: string,
    versionId: string,
    body: Record<string, unknown>,
    pageVersion: number,
    idempotencyKey: string,
  ) {
    return this.request<WikiPage>(
      "PATCH",
      `/api/v1/wiki/pages/${pageId}/drafts/${versionId}`,
      body,
      {
        "Idempotency-Key": idempotencyKey,
        "If-Match": `"v${pageVersion}"`,
      },
    );
  }

  listWikiPageVersions(pageId: string) {
    return this.request<{ items: WikiPageVersion[] }>(
      "GET",
      `/api/v1/wiki/pages/${pageId}/versions`,
    );
  }

  getWikiPageVersion(pageId: string, versionId: string) {
    return this.request<WikiPageVersion>(
      "GET",
      `/api/v1/wiki/pages/${pageId}/versions/${versionId}`,
    );
  }

  listClaims(spaceId: string) {
    return this.request<{ items: Claim[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/claims`,
    );
  }

  listEvaluationSuites(spaceId: string) {
    return this.request<EvaluationSuite[]>(
      "GET",
      `/api/v1/spaces/${spaceId}/evaluation-suites`,
    );
  }

  createEvaluationSuite(spaceId: string, body: Record<string, unknown>) {
    return this.request<EvaluationSuite>(
      "POST",
      `/api/v1/spaces/${spaceId}/evaluation-suites`,
      body,
      { "Idempotency-Key": crypto.randomUUID() },
    );
  }

  listReleaseCandidates(spaceId: string) {
    return this.request<{ items: ReleaseCandidate[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/release-candidates`,
    );
  }

  createReleaseCandidate(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<ReleaseCandidate>(
      "POST",
      `/api/v1/spaces/${spaceId}/release-candidates`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  publishReleaseCandidate(
    candidateId: string,
    body: { reason: string; channel?: string },
    idempotencyKey: string,
  ) {
    return this.request<ReleaseCandidate>(
      "POST",
      `/api/v1/release-candidates/${candidateId}/publish`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  listReleases(spaceId: string) {
    return this.request<{ items: KnowledgeRelease[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/releases`,
    );
  }

  getRelease(releaseId: string) {
    return this.request<KnowledgeRelease>(
      "GET",
      `/api/v1/releases/${releaseId}`,
    );
  }

  getReleasePointer(spaceId: string, channel = "stable") {
    return this.request<Record<string, unknown>>(
      "GET",
      this.withQuery(`/api/v1/spaces/${spaceId}/release-pointer`, { channel }),
    );
  }

  switchReleasePointer(
    spaceId: string,
    body: { release_id: string; channel: string; reason: string },
    expectedVersion: number,
    idempotencyKey: string,
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/api/v1/spaces/${spaceId}/release-pointer`,
      body,
      {
        "Idempotency-Key": idempotencyKey,
        "If-Match": `"v${expectedVersion}"`,
      },
    );
  }

  exportRelease(releaseId: string) {
    return this.request<Record<string, unknown>>(
      "GET",
      `/api/v1/releases/${releaseId}/export?format=json`,
    );
  }

  rebuildReleaseProjection(releaseId: string, idempotencyKey: string) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/api/v1/releases/${releaseId}/projections/rebuild`,
      undefined,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  askRelease(releaseId: string, body: Record<string, unknown>) {
    return this.request<QueryAnswer>(
      "POST",
      `/api/v1/releases/${releaseId}/queries`,
      body,
    );
  }

  traverseReleaseGraph(releaseId: string, startEntityId: string, maxDepth = 1) {
    return this.request<Record<string, unknown>>(
      "GET",
      this.withQuery(`/api/v1/releases/${releaseId}/graph/traverse`, {
        start_entity_id: startEntityId,
        max_depth: maxDepth,
        mode: "TRAVERSE",
      }),
    );
  }

  createReviewPolicy(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/api/v1/spaces/${spaceId}/review-policies`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  createReviewCase(
    spaceId: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ) {
    return this.request<ReviewCase>(
      "POST",
      `/api/v1/spaces/${spaceId}/review-cases`,
      body,
      { "Idempotency-Key": idempotencyKey },
    );
  }

  listReviewCases(spaceId: string) {
    return this.request<{ items: ReviewCase[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/review-cases`,
    );
  }

  listConflicts(spaceId: string) {
    return this.request<{ items: ConflictCase[] }>(
      "GET",
      `/api/v1/spaces/${spaceId}/conflicts`,
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
