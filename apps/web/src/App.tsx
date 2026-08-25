import {
  Component,
  type ErrorInfo,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, NexweaveApi } from "./api";
import { TaskCenter } from "./TaskCenter";
import type {
  AuditLog,
  GovernanceObject,
  Member,
  Organization,
  Principal,
  Role,
  RoleDescriptor,
  Space,
  User,
} from "./types";

const SESSION_KEY = "nexweave.m1.access-token";
const SPACE_KEY = "nexweave.m1.space";

const NAVIGATION = [
  ["overview", "总览", "01"],
  ["spaces", "知识空间", "02"],
  ["sources", "资料中心", "03"],
  ["schemas", "Schema", "04"],
  ["compile", "任务中心", "05"],
  ["wiki", "Wiki", "06"],
  ["claims", "Claims", "07"],
  ["graph", "知识图谱", "08"],
  ["conflicts", "冲突中心", "09"],
  ["reviews", "审核中心", "10"],
  ["quality", "质量中心", "11"],
  ["releases", "发布中心", "12"],
  ["ask", "知识问答", "13"],
  ["domain-packs", "领域包", "14"],
  ["integrations", "集成", "15"],
  ["admin", "平台管理", "16"],
] as const;

const FUTURE_BOUNDARIES: Record<string, [string, string]> = {
  sources: ["资料中心", "M3 开始实现资料接入；M1 仅提供可信对象底座。"],
  schemas: [
    "Schema",
    "Schema Registry 不在 M2 边界；当前没有伪造 Schema 数据。",
  ],
  wiki: ["Wiki", "M5 开始形成知识草稿；当前没有静态内容冒充知识。"],
  claims: ["Claims", "M5 开始形成可验证声明；当前没有固定 JSON。"],
  graph: ["知识图谱", "M6 开始实现图谱探索。"],
  conflicts: ["冲突中心", "M6 开始实现冲突检测与治理。"],
  reviews: ["审核中心", "M7 开始实现人工审核工作流。"],
  quality: ["质量中心", "M6 开始实现质量评估。"],
  releases: ["发布中心", "M8 开始实现不可变发布。"],
  ask: ["知识问答", "M10 开始实现基于已发布知识的问答。"],
  "domain-packs": ["领域包", "M4 开始实现声明式领域包。"],
  integrations: ["集成", "后续 Milestone 才会开放连接器实例和 GridCrew 集成。"],
};

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY));
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [booting, setBooting] = useState(Boolean(token));
  const [route, setRoute] = useState(readRoute);
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState(
    () => localStorage.getItem(SPACE_KEY) ?? "",
  );
  const [globalError, setGlobalError] = useState("");
  const api = useMemo(() => new NexweaveApi(token ?? undefined), [token]);

  const loadSpaces = useCallback(async () => {
    const result = await api.spaces();
    setSpaces(result.items);
    setSelectedSpaceId((current) => {
      const next = result.items.some((space) => space.id === current)
        ? current
        : (result.items[0]?.id ?? "");
      if (next) localStorage.setItem(SPACE_KEY, next);
      return next;
    });
  }, [api]);

  useEffect(() => {
    const onPopState = () => setRoute(readRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!token) {
      setBooting(false);
      setPrincipal(null);
      return;
    }
    let active = true;
    setBooting(true);
    api
      .me()
      .then(async (identity) => {
        if (!active) return;
        setPrincipal(identity);
        await loadSpaces();
      })
      .catch((error: unknown) => {
        if (!active) return;
        sessionStorage.removeItem(SESSION_KEY);
        setToken(null);
        setGlobalError(messageOf(error));
      })
      .finally(() => active && setBooting(false));
    return () => {
      active = false;
    };
  }, [api, loadSpaces, token]);

  function navigate(next: string) {
    history.pushState({}, "", `/${next}`);
    setRoute(next);
  }

  function selectSpace(id: string) {
    setSelectedSpaceId(id);
    localStorage.setItem(SPACE_KEY, id);
  }

  function logOut() {
    sessionStorage.removeItem(SESSION_KEY);
    setToken(null);
    setPrincipal(null);
  }

  if (booting) return <LoadingScreen />;
  if (!token || !principal) {
    return (
      <Login
        initialError={globalError}
        onSession={(nextToken) => {
          sessionStorage.setItem(SESSION_KEY, nextToken);
          setGlobalError("");
          setToken(nextToken);
        }}
      />
    );
  }

  const selectedSpace = spaces.find((space) => space.id === selectedSpaceId);
  const canAdmin = hasAnyRole(principal, "platform_admin", "tenant_admin");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate("overview")}>
          <span className="brand-mark">N</span>
          <span>NEXWEAVE</span>
        </button>
        <div className="space-picker">
          <label htmlFor="space-picker">当前空间</label>
          <select
            id="space-picker"
            value={selectedSpaceId}
            onChange={(event) => selectSpace(event.target.value)}
          >
            {!spaces.length && <option value="">尚无空间</option>}
            {spaces.map((space) => (
              <option value={space.id} key={space.id}>
                {space.display_name}
              </option>
            ))}
          </select>
        </div>
        <nav aria-label="主导航">
          {NAVIGATION.map(([key, label, index]) => {
            const disabled = key === "admin" && !canAdmin;
            return (
              <button
                className={route === key ? "active" : ""}
                disabled={disabled}
                key={key}
                onClick={() => navigate(key)}
              >
                <span>{index}</span>
                {label}
              </button>
            );
          })}
        </nav>
        <div className="identity-card">
          <span className="avatar">
            {principal.subject.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{principal.subject}</strong>
            <small>{principal.roles.join(" · ")}</small>
          </div>
          <button onClick={logOut}>退出</button>
        </div>
      </aside>
      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="eyebrow">R1 · M2 RELIABLE WORKFLOW KERNEL</span>
            <strong>{selectedSpace?.display_name ?? "租户工作台"}</strong>
          </div>
          <span className="status-chip">
            <i />
            身份已验证
          </span>
        </header>
        {globalError && (
          <div className="error-banner" role="alert">
            {globalError}
            <button onClick={() => setGlobalError("")}>关闭</button>
          </div>
        )}
        <PageBoundary key={route}>
          {route === "overview" && (
            <Overview api={api} principal={principal} spaces={spaces} />
          )}
          {route === "spaces" && (
            <SpacesPage
              api={api}
              principal={principal}
              spaces={spaces}
              selected={selectedSpace}
              onSelect={selectSpace}
              onChanged={loadSpaces}
            />
          )}
          {route === "compile" && (
            <TaskCenter
              api={api}
              principal={principal}
              spaceId={selectedSpaceId}
            />
          )}
          {route === "admin" &&
            (canAdmin ? <AdminPage api={api} /> : <Denied />)}
          {FUTURE_BOUNDARIES[route] && (
            <FuturePage
              title={FUTURE_BOUNDARIES[route][0]}
              boundary={FUTURE_BOUNDARIES[route][1]}
            />
          )}
          {!NAVIGATION.some(([key]) => key === route) && <NotFound />}
        </PageBoundary>
      </main>
    </div>
  );
}

function Login({
  initialError,
  onSession,
}: {
  initialError: string;
  onSession: (token: string) => void;
}) {
  const [subject, setSubject] = useState("local-admin");
  const [error, setError] = useState(initialError);
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      const session = await new NexweaveApi().login(subject);
      onSession(session.access_token);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">N</span>NEXWEAVE
        </div>
        <span className="eyebrow">TRUSTED KNOWLEDGE PLATFORM</span>
        <h1>把权限边界，变成知识可信的起点。</h1>
        <p>M2 已在平台底座上接通可靠工作流内核与真实任务投影。</p>
      </section>
      <form className="login-card" onSubmit={submit}>
        <span className="step">01 / LOCAL DEVELOPMENT</span>
        <h2>进入平台</h2>
        <p>本地开发环境使用已配置的测试身份。生产环境切换为 OIDC。</p>
        <label htmlFor="subject">开发身份</label>
        <input
          id="subject"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          required
        />
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <button className="primary" disabled={working} type="submit">
          {working ? "正在验证…" : "验证身份并进入"}
        </button>
        <small>Local identity provider · 仅限开发环境</small>
      </form>
    </main>
  );
}

function Overview({
  api,
  principal,
  spaces,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaces: Space[];
}) {
  const [audits, setAudits] = useState<AuditLog[]>([]);
  const [auditError, setAuditError] = useState("");
  const canAudit = hasAnyRole(
    principal,
    "platform_admin",
    "tenant_admin",
    "auditor",
  );
  const loadAudits = useCallback(async () => {
    if (!canAudit) return;
    setAuditError("");
    try {
      setAudits((await api.audits()).items);
    } catch (error) {
      setAuditError(messageOf(error));
    }
  }, [api, canAudit]);
  useEffect(() => void loadAudits(), [loadAudits]);
  const active = spaces.filter((space) => space.status === "ACTIVE").length;
  const denied = audits.filter((item) => item.outcome === "DENIED").length;
  return (
    <section className="page">
      <PageTitle
        index="01"
        title="平台总览"
        description="来自真实平台服务的当前租户视图。"
      />
      {auditError && (
        <div className="form-error" role="alert">
          {auditError}
          <button onClick={() => void loadAudits()}>重试</button>
        </div>
      )}
      <div className="metric-grid">
        <Metric
          value={spaces.length}
          label="知识空间"
          detail={`${active} 个活跃`}
        />
        <Metric
          value={audits.length}
          label="近期审计事件"
          detail="最多 50 条"
        />
        <Metric value={denied} label="拒绝事件" detail="默认拒绝策略" />
        <Metric
          value={principal.clearance}
          label="当前密级"
          detail="身份声明"
        />
      </div>
      <div className="two-column">
        <Panel title="空间状态">
          <DataTable
            headers={["空间", "状态", "版本"]}
            rows={spaces.map((space) => [
              space.display_name,
              space.status,
              `v${space.version}`,
            ])}
            empty="尚未创建知识空间"
          />
        </Panel>
        <Panel title="最近审计">
          <DataTable
            headers={["动作", "结果", "时间"]}
            rows={audits
              .slice(0, 6)
              .map((item) => [
                item.action,
                item.outcome,
                formatDate(item.occurred_at),
              ])}
            empty={canAudit ? "尚无审计记录" : "当前角色无审计查看权限"}
          />
        </Panel>
      </div>
    </section>
  );
}

function SpacesPage({
  api,
  principal,
  spaces,
  selected,
  onSelect,
  onChanged,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaces: Space[];
  selected?: Space;
  onSelect: (id: string) => void;
  onChanged: () => Promise<void>;
}) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState("");
  const canCreate = hasAnyRole(principal, "platform_admin", "tenant_admin");
  const canManage = canCreate || hasAnyRole(principal, "space_admin");

  const refreshMembers = useCallback(async () => {
    if (!selected || !canManage) return setMembers([]);
    const value = await api.members(selected.id);
    setMembers(value.items);
  }, [api, canManage, selected]);

  const refreshDirectory = useCallback(async () => {
    const [organizationPage, userPage] = await Promise.all([
      api.organizations(),
      canManage ? api.users() : Promise.resolve({ items: [] as User[] }),
    ]);
    setOrganizations(organizationPage.items);
    setUsers(userPage.items);
  }, [api, canManage]);

  useEffect(() => {
    void refreshDirectory().catch((e) => setError(messageOf(e)));
  }, [refreshDirectory]);
  useEffect(() => {
    void refreshMembers().catch((e) => setError(messageOf(e)));
  }, [refreshMembers]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const created = await api.createSpace({
        organization_id: data.get("organization_id"),
        slug: data.get("slug"),
        display_name: data.get("display_name"),
        description: data.get("description"),
        default_classification: data.get("default_classification"),
      });
      event.currentTarget.reset();
      await onChanged();
      onSelect(created.id);
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  async function edit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    try {
      await api.updateSpace(selected, {
        display_name: data.get("display_name"),
        description: data.get("description"),
      });
      await onChanged();
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  async function grant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    try {
      await api.grantMember(selected.id, String(data.get("subject_id")), {
        subject_type: "USER",
        roles: [data.get("role")],
        clearance: data.get("clearance"),
      });
      await refreshMembers();
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  async function retry() {
    setError("");
    try {
      await Promise.all([onChanged(), refreshDirectory(), refreshMembers()]);
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  return (
    <section className="page">
      <PageTitle
        index="02"
        title="知识空间"
        description="空间、成员、密级与归档生命周期均由真实 API 驱动。"
      />
      {error && (
        <div className="form-error" role="alert">
          {error}
          <button onClick={() => void retry()}>重试</button>
        </div>
      )}
      <div className="space-layout">
        <Panel title={`空间目录 · ${spaces.length}`}>
          <div className="space-list">
            {spaces.map((space) => (
              <button
                className={selected?.id === space.id ? "selected" : ""}
                key={space.id}
                onClick={() => onSelect(space.id)}
              >
                <strong>{space.display_name}</strong>
                <span>
                  {space.slug} · {space.status} · v{space.version}
                </span>
              </button>
            ))}
            {!spaces.length && <Empty text="尚未创建空间" />}
          </div>
        </Panel>
        <div className="stack">
          {selected ? (
            <Panel title="空间详情">
              <form className="compact-form" onSubmit={edit}>
                <label>
                  名称
                  <input
                    name="display_name"
                    defaultValue={selected.display_name}
                    disabled={!canManage || selected.status === "ARCHIVED"}
                  />
                </label>
                <label>
                  描述
                  <textarea
                    name="description"
                    defaultValue={selected.description}
                    disabled={!canManage || selected.status === "ARCHIVED"}
                  />
                </label>
                <div className="form-actions">
                  <span className={`pill ${selected.status.toLowerCase()}`}>
                    {selected.status}
                  </span>
                  {canManage && selected.status === "ACTIVE" && (
                    <button className="primary">保存变更</button>
                  )}
                  {canManage && selected.status === "ACTIVE" && (
                    <button
                      type="button"
                      className="danger"
                      onClick={() =>
                        void api
                          .archiveSpace(selected)
                          .then(onChanged)
                          .catch((e) => setError(messageOf(e)))
                      }
                    >
                      归档空间
                    </button>
                  )}
                </div>
              </form>
            </Panel>
          ) : (
            <Panel title="空间详情">
              <Empty text="选择或创建一个空间" />
            </Panel>
          )}
          {canCreate && (
            <Panel title="创建空间">
              <form className="compact-form three" onSubmit={create}>
                <label>
                  组织
                  <select name="organization_id" required>
                    {organizations.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  标识
                  <input
                    name="slug"
                    pattern="[a-z0-9][a-z0-9-]*"
                    placeholder="quality-platform"
                    required
                  />
                </label>
                <label>
                  名称
                  <input name="display_name" required />
                </label>
                <label className="wide">
                  描述
                  <textarea name="description" />
                </label>
                <label>
                  默认密级
                  <select name="default_classification">
                    <option>INTERNAL</option>
                    <option>CONFIDENTIAL</option>
                    <option>HIGHLY_RESTRICTED</option>
                  </select>
                </label>
                <button className="primary">创建</button>
              </form>
            </Panel>
          )}
          {selected && canManage && (
            <Panel title="成员与角色">
              <form className="inline-form" onSubmit={grant}>
                <select name="subject_id" aria-label="成员" required>
                  <option value="">选择成员</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.display_name}
                    </option>
                  ))}
                </select>
                <select name="role" aria-label="角色">
                  <option>consumer</option>
                  <option>knowledge_engineer</option>
                  <option>reviewer</option>
                  <option>publisher</option>
                  <option>space_admin</option>
                  <option>auditor</option>
                </select>
                <select name="clearance" aria-label="密级">
                  <option>INTERNAL</option>
                  <option>CONFIDENTIAL</option>
                  <option>HIGHLY_RESTRICTED</option>
                </select>
                <button className="primary">授权</button>
              </form>
              <DataTable
                headers={["成员", "角色", "密级", "操作"]}
                rows={members.map((member) => [
                  users.find((user) => user.id === member.subject_id)
                    ?.display_name ?? member.subject_id.slice(0, 8),
                  member.roles.join(", "),
                  member.clearance,
                  member.status === "ACTIVE" ? (
                    <button
                      className="text-danger"
                      onClick={() =>
                        void api
                          .revokeMember(selected.id, member.subject_id)
                          .then(refreshMembers)
                          .catch((e) => setError(messageOf(e)))
                      }
                    >
                      撤销
                    </button>
                  ) : (
                    member.status
                  ),
                ])}
                empty="尚无成员"
              />
            </Panel>
          )}
        </div>
      </div>
    </section>
  );
}

type AdminTab =
  | "users"
  | "roles"
  | "models"
  | "prompts"
  | "connectors"
  | "audit";

function AdminPage({ api }: { api: NexweaveApi }) {
  const [tab, setTab] = useState<AdminTab>("users");
  const [items, setItems] = useState<
    Array<User | RoleDescriptor | GovernanceObject | AuditLog>
  >([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      if (tab === "users") setItems((await api.users()).items);
      if (tab === "roles") setItems((await api.roles()).items);
      if (tab === "audit") setItems((await api.audits()).items);
      if (tab === "models")
        setItems((await api.listGovernance("model-profiles")).items);
      if (tab === "prompts")
        setItems((await api.listGovernance("prompt-versions")).items);
      if (tab === "connectors")
        setItems((await api.listGovernance("connector-definitions")).items);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, tab]);
  useEffect(() => {
    void load();
  }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      if (tab === "users") {
        await api.createUser({
          issuer: data.get("issuer"),
          subject: data.get("subject"),
          display_name: data.get("display_name"),
          clearance: "INTERNAL",
          tenant_roles: [],
        });
      }
      if (tab === "models") {
        await api.createGovernance("model-profiles", {
          name: data.get("name"),
          provider: data.get("provider"),
          model_name: data.get("model_name"),
          externally_hosted: false,
          maximum_classification: "INTERNAL",
          config: {},
        });
      }
      if (tab === "prompts") {
        await api.createGovernance("prompt-versions", {
          prompt_key: data.get("prompt_key"),
          content: data.get("content"),
          output_contract: {},
        });
      }
      if (tab === "connectors") {
        await api.createGovernance("connector-definitions", {
          name: data.get("name"),
          connector_type: data.get("connector_type"),
          config_schema: {},
        });
      }
      form.reset();
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  return (
    <section className="page">
      <PageTitle
        index="16"
        title="平台管理"
        description="身份权限、治理配置与审计证据的统一入口。"
      />
      <div className="tabs" role="tablist">
        {(
          [
            "users",
            "roles",
            "models",
            "prompts",
            "connectors",
            "audit",
          ] as AdminTab[]
        ).map((item) => (
          <button
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? "active" : ""}
            key={item}
            onClick={() => setTab(item)}
          >
            {adminLabel(item)}
          </button>
        ))}
      </div>
      {error && (
        <div className="form-error" role="alert">
          {error}
          <button onClick={() => void load()}>重试</button>
        </div>
      )}
      {tab === "users" && <CreateUserForm onSubmit={create} />}
      {tab === "models" && <CreateModelForm onSubmit={create} />}
      {tab === "prompts" && <CreatePromptForm onSubmit={create} />}
      {tab === "connectors" && <CreateConnectorForm onSubmit={create} />}
      <Panel title={`${adminLabel(tab)} · ${items.length}`}>
        <DataTable
          headers={adminHeaders(tab)}
          rows={items.map((item) => adminRow(tab, item))}
          empty={loading ? "正在加载…" : "暂无记录"}
        />
      </Panel>
    </section>
  );
}

function CreateUserForm({
  onSubmit,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Panel title="创建用户">
      <form className="inline-form" onSubmit={onSubmit}>
        <input
          name="issuer"
          defaultValue="local"
          aria-label="签发方"
          required
        />
        <input
          name="subject"
          placeholder="唯一身份标识"
          aria-label="身份标识"
          required
        />
        <input
          name="display_name"
          placeholder="显示名称"
          aria-label="显示名称"
          required
        />
        <button className="primary">创建</button>
      </form>
    </Panel>
  );
}

function CreateModelForm({
  onSubmit,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Panel title="登记模型配置">
      <form className="inline-form" onSubmit={onSubmit}>
        <input name="name" placeholder="配置名称" required />
        <input name="provider" placeholder="提供方" required />
        <input name="model_name" placeholder="模型名称" required />
        <button className="primary">登记</button>
      </form>
    </Panel>
  );
}

function CreatePromptForm({
  onSubmit,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Panel title="创建提示词版本">
      <form className="inline-form" onSubmit={onSubmit}>
        <input name="prompt_key" placeholder="提示词键" required />
        <input name="content" placeholder="提示词内容" required />
        <button className="primary">创建版本</button>
      </form>
    </Panel>
  );
}

function CreateConnectorForm({
  onSubmit,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Panel title="登记连接器定义">
      <form className="inline-form" onSubmit={onSubmit}>
        <input name="name" placeholder="定义名称" required />
        <input name="connector_type" placeholder="连接器类型" required />
        <button className="primary">登记</button>
      </form>
    </Panel>
  );
}

function FuturePage({ title, boundary }: { title: string; boundary: string }) {
  return (
    <section className="page">
      <PageTitle index="BOUNDARY" title={title} description={boundary} />
      <div className="future-card">
        <span>NOT IMPLEMENTED IN M2</span>
        <h2>边界已保留，能力尚未进入开发。</h2>
        <p>
          这里不会展示 Mock、固定 JSON 或 LLM 文本。相关能力只能在对应 Milestone
          正式下发后实现。
        </p>
      </div>
    </section>
  );
}

class PageBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Keep the authenticated shell available while the page fallback is shown.
    void _error;
    void _info;
  }

  render() {
    if (this.state.failed) {
      return (
        <section className="page">
          <div className="form-error" role="alert">
            页面暂时无法显示，请刷新后重试。
            <button onClick={() => location.reload()}>刷新</button>
          </div>
        </section>
      );
    }
    return this.props.children;
  }
}

function PageTitle({
  index,
  title,
  description,
}: {
  index: string;
  title: string;
  description: string;
}) {
  return (
    <header className="page-title">
      <span>{index}</span>
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </header>
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
}: {
  value: string | number;
  label: string;
  detail: string;
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: ReactNode[][];
  empty: string;
}) {
  if (!rows.length) return <Empty text={empty} />;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
function LoadingScreen() {
  return (
    <main className="loading">
      <span className="brand-mark">N</span>
      <p>正在恢复可信会话…</p>
    </main>
  );
}
function Denied() {
  return (
    <section className="page">
      <PageTitle
        index="403"
        title="无权访问"
        description="当前身份不具备平台管理权限。该拒绝由服务端策略再次执行。"
      />
    </section>
  );
}
function NotFound() {
  return (
    <section className="page">
      <PageTitle
        index="404"
        title="页面不存在"
        description="请从左侧导航选择一个平台入口。"
      />
    </section>
  );
}

function readRoute() {
  const route = location.pathname.replace(/^\//, "").split("/")[0];
  return route || "overview";
}

function hasAnyRole(principal: Principal, ...roles: Role[]) {
  return roles.some((role) => principal.roles.includes(role));
}

function messageOf(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "发生未知错误，请重试。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function adminLabel(tab: AdminTab) {
  return {
    users: "用户",
    roles: "角色权限",
    models: "模型配置",
    prompts: "提示词版本",
    connectors: "连接器定义",
    audit: "审计日志",
  }[tab];
}

function adminHeaders(tab: AdminTab) {
  if (tab === "users") return ["名称", "身份标识", "密级", "状态"];
  if (tab === "roles") return ["角色", "允许动作", "策略"];
  if (tab === "audit") return ["动作", "资源", "结果", "时间"];
  return ["名称 / 键", "类型 / 模型", "状态", "版本"];
}

function adminRow(
  tab: AdminTab,
  item: User | RoleDescriptor | GovernanceObject | AuditLog,
): ReactNode[] {
  if (tab === "users") {
    const user = item as User;
    return [user.display_name, user.subject, user.clearance, user.status];
  }
  if (tab === "roles") {
    const role = item as RoleDescriptor;
    return [role.role, role.actions.join(", "), "default-deny"];
  }
  if (tab === "audit") {
    const audit = item as AuditLog;
    return [
      audit.action,
      audit.resource_type,
      audit.outcome,
      formatDate(audit.occurred_at),
    ];
  }
  const value = item as GovernanceObject;
  return [
    value.name ?? value.prompt_key ?? "—",
    value.model_name ?? value.connector_type ?? "—",
    value.status,
    `v${value.version ?? value.revision ?? 1}`,
  ];
}
