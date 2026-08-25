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

  private async request<T>(
    method: string,
    path: string,
    body?: Record<string, unknown>,
    extraHeaders: Record<string, string> = {},
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
      body: body ? JSON.stringify(body) : undefined,
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
    return (await response.json()) as T;
  }
}
