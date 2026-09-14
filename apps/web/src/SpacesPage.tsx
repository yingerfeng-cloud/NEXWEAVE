import { type FormEvent, useCallback, useEffect, useState } from "react";

import { messageOf, type NexweaveApi } from "./api";
import {
  DataTable,
  EmptyState as Empty,
  PageHeader as PageTitle,
  Panel,
  StatusPill,
} from "./design-system/ui";
import type {
  Member,
  Organization,
  Principal,
  Role,
  Space,
  User,
} from "./types";

export function SpacesPage({
  api,
  principal,
  spaces,
  selected,
  onSelect,
  onChanged,
  onNavigate,
}: {
  api: NexweaveApi;
  principal: Principal;
  spaces: Space[];
  selected?: Space;
  onSelect: (id: string) => void;
  onChanged: () => Promise<void>;
  onNavigate?: (path: string) => void;
}) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshIssue, setRefreshIssue] = useState("");
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");
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
    void refreshDirectory().catch((nextError) =>
      setError(messageOf(nextError)),
    );
  }, [refreshDirectory]);
  useEffect(() => {
    void refreshMembers().catch((nextError) => setError(messageOf(nextError)));
  }, [refreshMembers]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setError("");
    setNotice("");
    setRefreshIssue("");
    setSubmitting(true);
    try {
      const created = await api.createSpace({
        organization_id: data.get("organization_id"),
        slug: data.get("slug"),
        display_name: data.get("display_name"),
        description: data.get("description"),
        default_classification: data.get("default_classification"),
      });
      form.reset();
      setCreating(false);
      onSelect(created.id);
      setNotice(`空间“${created.display_name}”已创建，正在刷新空间目录。`);
      try {
        await onChanged();
        setNotice(
          `空间“${created.display_name}”已创建并已切换。下一步可进入资料中心导入并解析资料。`,
        );
      } catch {
        // The POST is already committed. A refresh failure must not turn a
        // successful creation into a misleading network error or invite a
        // duplicate submission.
        setNotice(`空间“${created.display_name}”已创建，但目录尚未刷新。`);
        setRefreshIssue(
          "空间已创建，但目录刷新暂时失败；可以安全重试目录刷新。",
        );
      }
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setSubmitting(false);
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
    setRefreshIssue("");
    try {
      await Promise.all([onChanged(), refreshDirectory(), refreshMembers()]);
    } catch (nextError) {
      setRefreshIssue(`目录刷新失败：${messageOf(nextError)}`);
    }
  }

  return (
    <section className="page">
      <PageTitle
        title="知识空间"
        description="按知识空间组织成员、资料、知识模型、发布与访问边界。"
        actions={
          canCreate ? (
            <button
              type="button"
              className="primary"
              onClick={() => setCreating(true)}
            >
              + 创建知识空间
            </button>
          ) : undefined
        }
      />
      {notice && (
        <div className="notice-banner" role="status">
          <span>{notice}</span>
          {onNavigate && (
            <button type="button" onClick={() => onNavigate("sources")}>
              前往资料中心
            </button>
          )}
        </div>
      )}
      {error && (
        <div className="form-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => void retry()}>
            重试
          </button>
        </div>
      )}
      {refreshIssue && (
        <div className="form-error" role="alert">
          <span>{refreshIssue}</span>
          <button type="button" onClick={() => void retry()}>
            重试目录刷新
          </button>
        </div>
      )}
      <div className="space-layout">
        <Panel title={`空间目录 · ${spaces.length}`}>
          <div className="space-list">
            <label className="list-search">
              搜索空间
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="按名称或标识搜索"
              />
            </label>
            {spaces
              .filter((space) =>
                `${space.display_name} ${space.slug}`
                  .toLowerCase()
                  .includes(query.toLowerCase()),
              )
              .map((space) => (
                <button
                  className={selected?.id === space.id ? "selected" : ""}
                  key={space.id}
                  onClick={() => onSelect(space.id)}
                >
                  <strong>{space.display_name}</strong>
                  <span>
                    {space.slug} · <StatusPill value={space.status} /> · v
                    {space.version}
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
                  <StatusPill value={selected.status} />
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
                          .catch((nextError) => setError(messageOf(nextError)))
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
          {canCreate && creating && (
            <div
              className="modal-backdrop"
              role="presentation"
              onMouseDown={() => setCreating(false)}
            >
              <section
                className="modal-panel"
                role="dialog"
                aria-modal="true"
                aria-label="创建知识空间"
                onMouseDown={(event) => event.stopPropagation()}
              >
                <header>
                  <h2>创建知识空间</h2>
                  <button
                    type="button"
                    aria-label="关闭"
                    onClick={() => setCreating(false)}
                  >
                    ×
                  </button>
                </header>
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
                      <option value="INTERNAL">内部</option>
                      <option value="CONFIDENTIAL">机密</option>
                      <option value="HIGHLY_RESTRICTED">高度受限</option>
                    </select>
                  </label>
                  <button
                    className="primary"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? "创建中…" : "创建"}
                  </button>
                </form>
              </section>
            </div>
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
                  <option value="consumer">使用者</option>
                  <option value="knowledge_engineer">知识工程师</option>
                  <option value="reviewer">审核员</option>
                  <option value="publisher">发布员</option>
                  <option value="space_admin">空间管理员</option>
                  <option value="auditor">审计员</option>
                </select>
                <select name="clearance" aria-label="密级">
                  <option value="INTERNAL">内部</option>
                  <option value="CONFIDENTIAL">机密</option>
                  <option value="HIGHLY_RESTRICTED">高度受限</option>
                </select>
                <button className="primary" type="submit">
                  授权
                </button>
              </form>
              <DataTable
                headers={["成员", "角色", "密级", "操作"]}
                rows={members.map((member) => [
                  users.find((user) => user.id === member.subject_id)
                    ?.display_name ?? member.subject_id.slice(0, 8),
                  member.roles.map(roleLabel).join("、"),
                  classificationLabel(member.clearance),
                  member.status === "ACTIVE" ? (
                    <button
                      type="button"
                      className="text-danger"
                      onClick={() =>
                        void api
                          .revokeMember(selected.id, member.subject_id)
                          .then(refreshMembers)
                          .catch((nextError) => setError(messageOf(nextError)))
                      }
                    >
                      撤销
                    </button>
                  ) : (
                    <StatusPill value={member.status} />
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

function hasAnyRole(principal: Principal, ...roles: Role[]) {
  return roles.some((role) => principal.roles.includes(role));
}

function roleLabel(role: string) {
  return (
    {
      consumer: "使用者",
      knowledge_engineer: "知识工程师",
      reviewer: "审核员",
      publisher: "发布员",
      space_admin: "空间管理员",
      auditor: "审计员",
      tenant_admin: "组织管理员",
    }[role] ?? role
  );
}

function classificationLabel(value: string) {
  return (
    {
      INTERNAL: "内部",
      CONFIDENTIAL: "机密",
      HIGHLY_RESTRICTED: "高度受限",
    }[value] ?? value
  );
}
