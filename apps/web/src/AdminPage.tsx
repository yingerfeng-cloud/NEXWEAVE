import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useState,
  useRef,
} from "react";

import { messageOf, type NexweaveApi } from "./api";
import {
  DataTable,
  ErrorState,
  PageHeader as PageTitle,
  Panel,
  Modal,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type { AuditLog, GovernanceObject, RoleDescriptor, User } from "./types";

type AdminTab =
  | "users"
  | "roles"
  | "models"
  | "prompts"
  | "connectors"
  | "audit";

export function AdminPage({
  api,
  developerMode = false,
}: {
  api: NexweaveApi;
  developerMode?: boolean;
}) {
  const [tab, setTab] = useState<AdminTab>("users");
  const [items, setItems] = useState<
    Array<User | RoleDescriptor | GovernanceObject | AuditLog>
  >([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  function selectTab(next: AdminTab) {
    setTab(next);
    setSearch("");
    setStatusFilter("");
    setError("");
  }
  const visibleItems = items
    .filter((item) => developerMode || !isDeveloperFixture(item))
    .filter((item) => matchesAdminFilter(item, search, statusFilter));

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
    if (savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError("");
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
      setCreating(false);
      await load();
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  return (
    <section className="page">
      <PageTitle
        title="平台管理"
        description="身份权限、治理配置与审计证据的统一入口。"
        actions={
          !["roles", "audit"].includes(tab) ? (
            <button
              type="button"
              className="primary"
              onClick={() => {
                setError("");
                setCreating(true);
              }}
            >
              + {createLabel(tab)}
            </button>
          ) : undefined
        }
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
            type="button"
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? "active" : ""}
            key={item}
            onClick={() => selectTab(item)}
          >
            {adminLabel(item)}
          </button>
        ))}
      </div>
      {error && !creating && <ErrorState message={error} onRetry={load} />}
      <div className="admin-toolbar">
        <label>
          搜索
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="名称、角色或状态"
          />
        </label>
        <label>
          状态
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">全部状态</option>
            <option value="ACTIVE">启用</option>
            <option value="DISABLED">停用</option>
            <option value="ARCHIVED">已归档</option>
          </select>
        </label>
      </div>
      {creating && (
        <Modal
          title={createLabel(tab)}
          busy={saving}
          onClose={() => setCreating(false)}
        >
          {error && <ErrorState message={error} onRetry={load} />}
          <fieldset className="modal-fields" disabled={saving}>
            {tab === "users" && <CreateUserForm onSubmit={create} />}
            {tab === "models" && <CreateModelForm onSubmit={create} />}
            {tab === "prompts" && <CreatePromptForm onSubmit={create} />}
            {tab === "connectors" && <CreateConnectorForm onSubmit={create} />}
          </fieldset>
          {saving && <p role="status">正在保存，请稍候…</p>}
        </Modal>
      )}
      <Panel title={`${adminLabel(tab)} · ${visibleItems.length}`}>
        <DataTable
          headers={adminHeaders(tab)}
          rows={visibleItems.map((item) => adminRow(tab, item))}
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
        <label>
          身份来源
          <input name="issuer" defaultValue="local" required />
        </label>
        <label>
          账号标识
          <input name="subject" placeholder="唯一身份标识" required />
        </label>
        <label>
          显示名称
          <input name="display_name" placeholder="显示名称" required />
        </label>
        <button className="primary" type="submit">
          创建
        </button>
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
        <label>
          配置名称
          <input name="name" required />
        </label>
        <label>
          提供方
          <input name="provider" required />
        </label>
        <label>
          模型名称
          <input name="model_name" required />
        </label>
        <button className="primary" type="submit">
          登记
        </button>
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
        <label>
          稳定标识
          <input name="prompt_key" required />
        </label>
        <label>
          提示词内容
          <input name="content" required />
        </label>
        <button className="primary" type="submit">
          创建版本
        </button>
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
        <label>
          连接器名称
          <input name="name" required />
        </label>
        <label>
          连接器类型
          <input name="connector_type" required />
        </label>
        <button className="primary" type="submit">
          登记
        </button>
      </form>
    </Panel>
  );
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
    return [
      user.display_name,
      <TechnicalDetails summary="查看身份标识">
        <code>{user.subject}</code>
      </TechnicalDetails>,
      <StatusPill value={user.clearance} />,
      <StatusPill value={user.status} />,
    ];
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
      <StatusPill value={audit.outcome} />,
      formatDate(audit.occurred_at),
    ];
  }
  const value = item as GovernanceObject;
  return [
    value.name ?? value.prompt_key ?? "—",
    value.model_name ?? value.connector_type ?? "—",
    <StatusPill value={value.status} />,
    `v${value.version ?? value.revision ?? 1}`,
  ];
}

function createLabel(tab: AdminTab) {
  return {
    users: "创建用户",
    models: "登记模型配置",
    prompts: "创建提示词版本",
    connectors: "登记连接器",
    roles: "",
    audit: "",
  }[tab];
}

function matchesAdminFilter(
  item: User | RoleDescriptor | GovernanceObject | AuditLog,
  search: string,
  status: string,
) {
  const text = JSON.stringify(item).toLowerCase();
  return (
    (!search.trim() || text.includes(search.trim().toLowerCase())) &&
    (!status || text.includes(status.toLowerCase()))
  );
}

function isDeveloperFixture(
  item: User | RoleDescriptor | GovernanceObject | AuditLog,
) {
  return /\bM\d+\b|E2E|synthetic|stub|isolat(?:ed|ion)|failure audit|technical pilot/i.test(
    JSON.stringify(item),
  );
}
