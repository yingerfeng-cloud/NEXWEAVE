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
