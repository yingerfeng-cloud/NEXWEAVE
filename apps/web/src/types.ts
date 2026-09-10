export type Role =
  | "platform_admin"
  | "tenant_admin"
  | "space_admin"
  | "knowledge_engineer"
  | "reviewer"
  | "publisher"
  | "consumer"
  | "auditor"
  | "service";

export type Principal = {
  actor_type: "USER" | "SERVICE";
  actor_id: string;
  tenant_id: string;
  subject: string;
  roles: Role[];
  clearance: string;
};

export type Session = {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  principal: Principal;
};

export type Organization = {
  id: string;
  tenant_id: string;
  slug: string;
  display_name: string;
  status: string;
  version: number;
};

export type Space = {
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
  updated_at: string;
};

export type Member = {
  id: string;
  subject_id: string;
  subject_type: "USER" | "SERVICE";
  roles: Role[];
  clearance: string;
  status: "ACTIVE" | "REVOKED";
  version: number;
};

export type User = {
  id: string;
  tenant_id: string;
  issuer: string;
  subject: string;
  display_name: string;
  clearance: string;
  tenant_roles: Role[];
  status: string;
};

export type RoleDescriptor = { role: Role; actions: string[] };

export type AuditLog = {
  id: string;
  occurred_at: string;
  actor_type: string;
  actor_id: string;
  action: string;
  resource_type: string;
  outcome: string;
  trace_id?: string;
};

export type GovernanceObject = {
  id: string;
  name?: string;
  prompt_key?: string;
  model_name?: string;
  connector_type?: string;
  status: string;
  version?: number;
  revision?: number;
  provider?: string;
  space_id?: string | null;
};

export type ConnectorInstance = {
  id: string;
  name: string;
  kind: "FILESYSTEM" | "S3" | "WEB_REST" | "GIT";
  status: string;
  classification: string;
  watermark: Record<string, unknown>;
  version: number;
};

export type ConnectorSyncRun = {
  id: string;
  connector_instance_id: string;
  workflow_id: string;
  temporal_run_id?: string;
  status: string;
  result_summary: Record<string, unknown>;
  error_code?: string;
  created_at: string;
};

export type CompileSourceRef = {
  source_version_id: string;
  source_checksum: string;
  parse_job_id: string;
  input_order: number;
};

export type CompileStep = {
  id: string;
  step_key: string;
  input_checksum: string;
  status: string;
  attempt: number;
  output_summary: Record<string, unknown>;
  error_code?: string | null;
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
  run_id?: string | null;
  mode: "FULL" | "INCREMENTAL" | "SOURCE_SCOPED" | "RECOMPILE";
  status: string;
  input_fingerprint: string;
  normalization_version: string;
  scope: Record<string, unknown>;
  progress: number;
  cost_summary: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_code?: string | null;
  error_detail?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  sources: CompileSourceRef[];
  steps: CompileStep[];
};

export type WikiPageVersion = {
  id: string;
  wiki_page_id: string;
  compile_job_id?: string | null;
  revision: number;
  generated_sections: Record<string, string>;
  protected_sections: Record<string, string>;
  properties: Record<string, unknown>;
  markdown: string;
  content_checksum: string;
  status: string;
  edit_reason?: string | null;
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
  current_version_id?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  current_version?: WikiPageVersion | null;
  outbound_links?: Record<string, unknown>[];
  backlinks?: Record<string, unknown>[];
  comments?: Record<string, unknown>[];
  evidence_candidates?: Record<string, unknown>[];
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
  focus_page_id?: string | null;
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
  subject_entity_id: string;
  predicate_key: string;
  object_value: Record<string, unknown>;
  statement: string;
  scope: Record<string, unknown>;
  valid_from?: string | null;
  valid_until?: string | null;
  confidence_level: "LOW" | "MEDIUM" | "HIGH";
  status: string;
  provenance: Record<string, unknown>;
  created_at: string;
  created_by: string;
};

export type ConflictCase = {
  id: string;
  cluster_key: string;
  kind: string;
  severity: string;
  blocking: boolean;
  status: string;
  suggested_action?: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type ReviewTask = {
  id: string;
  stage: string;
  status: string;
  assignee_id?: string | null;
  claimed_by?: string | null;
  due_at: string;
  escalation_count: number;
};

export type ReviewCase = {
  id: string;
  workflow_task_id: string;
  workflow_id: string;
  target_type: string;
  target_id: string;
  policy_id: string;
  risk_level: string;
  status: string;
  current_stage?: string | null;
  created_by: string;
  created_at: string;
  tasks: ReviewTask[];
};

export type WorkflowType =
  | "SOURCE_INGESTION"
  | "KNOWLEDGE_COMPILE"
  | "HUMAN_REVIEW"
  | "QUALITY_EVALUATION"
  | "KNOWLEDGE_RELEASE"
  | "DOMAIN_PACK_INSTALL"
  | "GRIDCREW_FEEDBACK_INGESTION";

export type WorkflowStatus =
  | "CREATED"
  | "STARTING"
  | "RUNNING"
  | "PAUSED"
  | "WAITING"
  | "WAITING_INPUT"
  | "CANCELLING"
  | "COMPENSATING"
  | "CANCELLED"
  | "SUCCEEDED"
  | "FAILED"
  | "TIMED_OUT"
  | "REJECTED";

export type WorkflowCommand =
  | "PAUSE"
  | "RESUME"
  | "CANCEL"
  | "CLAIM"
  | "REQUEST_INPUT"
  | "PROVIDE_INPUT"
  | "APPROVE"
  | "REJECT"
  | "RETRY";

export type WorkflowTask = {
  id: string;
  tenant_id: string;
  space_id: string;
  workflow_type: WorkflowType;
  business_key: string;
  display_name: string;
  workflow_id: string;
  temporal_run_id?: string;
  status: WorkflowStatus;
  version: number;
  progress: number;
  current_step?: string;
  input_refs: Record<string, string>;
  result_summary: Record<string, unknown>;
  error_code?: string;
  error_detail?: string;
  projection_revision: number;
  projection_in_sync: boolean;
  last_reconciled_at?: string;
  created_at: string;
  updated_at: string;
};

export type WorkflowStep = {
  id: string;
  task_id: string;
  step_key: string;
  sequence: number;
  status: string;
  attempt: number;
  message: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
};

export type WorkflowEvent = {
  id: string;
  task_id: string;
  event_key: string;
  event_type: string;
  workflow_status: WorkflowStatus;
  step_key?: string;
  message: string;
  details: Record<string, unknown>;
  occurred_at: string;
};

export type WorkflowTaskDetail = {
  task: WorkflowTask;
  steps: WorkflowStep[];
  events: WorkflowEvent[];
  allowed_actions: WorkflowCommand[];
};

export type DataClassification =
  | "PUBLIC"
  | "INTERNAL"
  | "CONFIDENTIAL"
  | "HIGHLY_RESTRICTED";

export type SourceDocumentStatus = "REGISTERED" | "ACTIVE" | "ARCHIVED";
export type SourceVersionStatus =
  | "STORED"
  | "PARSING"
  | "PARTIAL"
  | "PARSED"
  | "FAILED"
  | "SUPERSEDED";
export type ParseJobStatus =
  | "CREATED"
  | "QUEUED"
  | "RUNNING"
  | "PARTIAL_FAILED"
  | "FAILED"
  | "SUCCEEDED"
  | "CANCELED";
export type AnchorStatus = "VALID" | "STALE" | "UNRESOLVED" | "REVOKED";

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
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
};

export type CompositionReport = {
  id: string;
  schema_version_id: string;
  input_checksum: string;
  result_checksum: string;
  report: Record<string, unknown>;
};

export type DomainPackVersion = {
  id: string;
  tenant_id: string;
  pack_key: string;
  pack_version: string;
  publisher: string;
  key_namespace: string;
  content_checksum: string;
  signature_key_id: string;
  status: string;
  created_at: string;
};

export type DomainPackInstallation = {
  id: string;
  tenant_id: string;
  space_id: string;
  domain_pack_version_id: string;
  schema_definition_id: string;
  requested_semantic_version: string;
  operation: "INSTALL" | "UPGRADE" | "DISABLE" | "ROLLBACK";
  previous_installation_id?: string | null;
  workflow_task_id?: string | null;
  workflow_id: string;
  run_id?: string | null;
  candidate_schema_version_id?: string | null;
  composition_report_id?: string | null;
  status:
    | "PLANNED"
    | "INSTALLING"
    | "ACTIVE"
    | "FAILED"
    | "ROLLING_BACK"
    | "ROLLED_BACK"
    | "DISABLED";
  version: number;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
};

export type SourceVersion = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_document_id: string;
  filename: string;
  content_type: string;
  size: number;
  checksum: string;
  object_version_id?: string | null;
  classification: DataClassification;
  status: SourceVersionStatus;
  version: number;
  active_parse_job_id?: string | null;
  latest_parse_job_id?: string | null;
  supersedes_source_version_id?: string | null;
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
  source_level?: string | null;
  tags: string[];
  valid_until?: string | null;
  status: SourceDocumentStatus;
  version: number;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  versions: SourceVersion[];
};

export type CursorPage<T> = {
  items: T[];
  next_cursor?: string | null;
};

export type SourceFilters = {
  search?: string;
  type?: string;
  status?: string;
  classification?: string;
  cursor?: string;
  limit?: number;
};

export type ParseFailureUnit = {
  id: string;
  parse_job_id: string;
  error_code: string;
  scope: "document" | "page" | "table" | "sheet" | "block";
  scope_ref: string;
  retryable: boolean;
  safe_detail: string;
};

export type ParseJob = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_version_id: string;
  status: ParseJobStatus;
  version: number;
  parser_id: string;
  parser_version: string;
  config_checksum: string;
  document_model_version: string;
  locator_version: string;
  ocr_provider_id?: string | null;
  ocr_provider_version?: string | null;
  workflow_id: string;
  temporal_run_id?: string | null;
  result_checksum?: string | null;
  failure_units: ParseFailureUnit[];
  created_at: string;
  updated_at: string;
};

export type Locator =
  | { kind: "page"; page: number }
  | { kind: "block"; block_id: string }
  | {
      kind: "character_range";
      start: number;
      end: number;
      text_basis: "normalized_utf8" | "source_utf8";
    }
  | {
      kind: "table_cell";
      table_id: string;
      row_start: number;
      row_end: number;
      column_start: number;
      column_end: number;
    }
  | {
      kind: "bounding_box";
      page: number;
      coordinate_system: "normalized_top_left";
      x: number;
      y: number;
      width: number;
      height: number;
    }
  | { kind: "time_range"; start_ms: number; end_ms: number };

export type DocumentSegment = {
  id: string;
  source_version_id: string;
  parse_job_id: string;
  sequence: number;
  block_type: string;
  structure_path: string;
  normalized_text?: string | null;
  derived_object_key?: string | null;
  text_checksum: string;
  page_number?: number | null;
  sheet_name?: string | null;
  table_id?: string | null;
  row_index?: number | null;
  column_index?: number | null;
  locators: Locator[];
  parser_id: string;
  parser_version: string;
  config_checksum: string;
  document_model_version: string;
  locator_version: string;
};

export type PreviewResponse = {
  source_version_id: string;
  parse_job_id: string;
  anchor_id?: string | null;
  anchor_status?: AnchorStatus | null;
  content_type: "text/plain" | "text/html";
  sanitized_content: string;
  locator_results: Array<{
    locator: Locator;
    matched: boolean;
    safe_detail: string;
  }>;
};

export type SourceUploadSession = {
  id: string;
  tenant_id: string;
  space_id: string;
  source_document_id: string;
  source_version_id: string;
  import_batch_id?: string | null;
  filename: string;
  content_type: string;
  expected_size: number;
  expected_checksum: string;
  object_key: string;
  status: string;
  version: number;
  upload_url: string;
  expires_at: string;
  created_at: string;
};

export type SourceUploadComplete = {
  source_id: string;
  source_version_id: string;
  parse_job_id: string;
  workflow_id: string;
  run_id?: string | null;
  duplicate_source_version_ids: string[];
  source_status: SourceDocumentStatus;
  version_status: SourceVersionStatus;
};

export type ImportBatchItem = {
  id: string;
  upload_session_id: string;
  source_document_id?: string | null;
  source_version_id?: string | null;
  filename: string;
  status:
    | "UPLOADING"
    | "PROCESSING"
    | "SUCCEEDED"
    | "PARTIAL"
    | "FAILED"
    | "CANCELED";
  error_code?: string | null;
  safe_detail?: string | null;
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
  items: ImportBatchItem[];
  created_at: string;
  created_by: string;
};

export type EvaluationCase = {
  case_key: string;
  case_type: string;
  question: string;
  expected_claim_ids: string[];
  expected_terms: string[];
  expect_refusal: boolean;
  metadata: Record<string, unknown>;
};

export type EvaluationSuite = {
  id: string;
  tenant_id: string;
  space_id: string;
  schema_version_id: string;
  suite_key: string;
  version: number;
  name: string;
  cases: EvaluationCase[];
  minimum_pass_rate: number;
  status: string;
  created_at: string;
  created_by: string;
};

export type LintFinding = {
  id: string;
  code: string;
  severity: string;
  blocking: boolean;
  object_type: string;
  object_id?: string | null;
  message: string;
};

export type ReleaseCandidate = {
  id: string;
  space_id: string;
  version: string;
  schema_version_id: string;
  prompt_version_id: string;
  model_profile_id: string;
  evaluation_suite_id: string;
  workflow_task_id: string;
  workflow_id: string;
  status: string;
  manifest_checksum: string;
  gate_summary: Record<string, unknown>;
  index_config: Record<string, unknown>;
  notes: string;
  created_at: string;
  lint_findings: LintFinding[];
};

export type KnowledgeRelease = {
  id: string;
  space_id: string;
  candidate_id: string;
  version: string;
  status: string;
  manifest_checksum: string;
  schema_version_id: string;
  model_profile_id: string;
  prompt_version_id: string;
  published_at: string;
  deprecated_at?: string | null;
  deprecation_reason?: string | null;
};

export type QueryCitation = {
  id: string;
  evidence_id: string;
  source_version_id: string;
  source_anchor_id: string;
  status: string;
};

export type QueryAnswer = {
  id: string;
  release_id: string;
  question: string;
  status: "COMPLETED" | "REFUSED" | "FAILED";
  direct_answer: string;
  key_basis: string[];
  uncertainty?: string | null;
  citations: QueryCitation[];
  conflicts: Record<string, unknown>[];
};

export type GraphTraverse = {
  release_id: string;
  start_entity_id: string;
  mode: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<{
    relation_id: string;
    relation_type_key: string;
    source_entity_id: string;
    target_entity_id: string;
    depth: number;
    evidence_ids: string[];
  }>;
  truncated: boolean;
};
