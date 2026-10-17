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
  const [identityIssuer, setIdentityIssuer] = useState("");
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
  useEffect(() => {
    if (!creating || tab !== "users") return;
    let active = true;
    void api
      .authConfig()
      .then((config) => {
        if (active) setIdentityIssuer(config.issuer ?? "");
      })
      .catch((cause) => {
        if (active) setError(messageOf(cause));
      });
    return () => {
      active = false;
    };
  }, [api, creating, tab]);

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
          externally_hosted: data.get("externally_hosted") === "on",
          maximum_classification:
            data.get("maximum_classification") || "INTERNAL",
          credential_ref: data.get("credential_ref") || null,
          config:
            data.get("provider") === "nexweave.local"
              ? { development_only: true }
              : {
                  capability: data.get("capability"),
                  revision: data.get("revision"),
                  response_model:
                    data.get("response_model") || data.get("model_name"),
                  ...(data.get("capability") === "embedding"
                    ? { dimensions: Number(data.get("dimensions")) }
                    : {}),
                },
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
            {tab === "users" && (
              <CreateUserForm onSubmit={create} issuer={identityIssuer} />
            )}
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
  issuer,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  issuer: string;
}) {
  return (
    <Panel title="创建用户">
      <form className="inline-form" onSubmit={onSubmit}>
        <label>
          身份来源
          <input name="issuer" value={issuer} readOnly required />
        </label>
        <label>
          账号标识
          <input name="subject" placeholder="唯一身份标识" required />
        </label>
        <label>
          显示名称
          <input name="display_name" placeholder="显示名称" required />
        </label>
        <button className="primary" type="submit" disabled={!issuer}>
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
          <select name="provider" required defaultValue="nexweave.local">
            <option value="nexweave.local">
              开发规则（仅开发，不支持语义embedding）
            </option>
            <option value="openai-compatible">
              兼容HTTP真实模型（需服务端配置）
            </option>
          </select>
        </label>
        <label>
          模型名称
          <input name="model_name" required />
        </label>
        <label>
          模型能力
          <select name="capability" defaultValue="structured_output">
            <option value="structured_output">原文抽取</option>
            <option value="embedding">真实embedding</option>
          </select>
        </label>
        <label>
          固定版本标识
          <input
            name="revision"
            placeholder="部署版本或权重revision，真实模型必填"
          />
        </label>
        <label>
          实际响应模型名
          <input name="response_model" placeholder="默认与模型名称一致" />
        </label>
        <label>
          Embedding维度
          <input name="dimensions" type="number" min="1" max="4096" />
        </label>
        <label>
          凭据引用
          <input
            name="credential_ref"
            placeholder="secret://model-gateway；不填写明文凭据"
          />
        </label>
        <label>
          最高密级
          <select name="maximum_classification" defaultValue="INTERNAL">
            <option value="INTERNAL">内部</option>
            <option value="CONFIDENTIAL">机密</option>
          </select>
        </label>
        <label>
          <input name="externally_hosted" type="checkbox" />
          外部托管模型
        </label>
        <p>
          模型端点由服务端配置管理；没有可用模型会明确失败。开发规则不提供语义能力。
        </p>
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
