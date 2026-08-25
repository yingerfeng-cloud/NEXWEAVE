import type {
  AuditLog,
  GovernanceObject,
  Member,
  Organization,
  Principal,
  RoleDescriptor,
  Session,
  Space,
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
    if (init.body) headers.set("Content-Type", "application/json");
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
}
