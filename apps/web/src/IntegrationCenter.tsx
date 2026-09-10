import { type FormEvent, useCallback, useEffect, useState } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type {
  ConnectorInstance,
  ConnectorSyncRun,
  GovernanceObject,
} from "./types";

export function IntegrationCenter({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [items, setItems] = useState<ConnectorInstance[]>([]);
  const [runs, setRuns] = useState<ConnectorSyncRun[]>([]);
  const [catalog, setCatalog] = useState<GovernanceObject[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncingId, setSyncingId] = useState("");
  const load = useCallback(async () => {
    if (!spaceId) {
      setItems([]);
      setRuns([]);
      setCatalog([]);
      setLoading(false);
      setError("");
      return;
    }
    setLoading(true);
    try {
      const [instances, definitions] = await Promise.all([
        api.connectorInstances(spaceId),
        api.listGovernance("connector-definitions"),
      ]);
      setItems(instances.items);
      setCatalog(definitions.items);
      setError("");
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setLoading(false);
    }
  }, [api, spaceId]);
  useEffect(() => void load(), [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.createConnectorInstance(spaceId, {
        definition_id: form.get("definition_id"),
        name: form.get("name"),
        kind: form.get("kind"),
        allowlist: String(form.get("allowlist"))
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        config: JSON.parse(String(form.get("config") || "{}")),
        field_mapping: {},
        classification: "INTERNAL",
      });
      (event.target as HTMLFormElement).reset();
      await load();
      setError("");
    } catch (nextError) {
      setError(messageOf(nextError));
    }
  }

  async function sync(instance: ConnectorInstance) {
    if (syncingId) return;
    setSyncingId(instance.id);
    try {
      const run = await api.startConnectorSync(spaceId, instance.id);
      setRuns((current) => [run, ...current]);
    } catch (nextError) {
      setError(messageOf(nextError));
    } finally {
      setSyncingId("");
    }
  }

  return (
    <section className="page">
      <PageHeader
        title="集成中心"
        description="从已批准的连接器目录创建只读集成；同步内容始终先进入资料版本与安全检查。"
        actions={
          <button
            type="button"
            className="primary"
            onClick={() => setCreateOpen((value) => !value)}
          >
            {createOpen ? "取消创建" : "+ 创建集成"}
          </button>
        }
      />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="集成实例、同步记录和资料投递都属于当前知识空间。"
        />
      )}
      <div className="integration-catalog">
        {catalog.map((item) => (
          <article className="data-card" key={item.id}>
            <h2>{item.name || "连接器"}</h2>
            <p>{item.connector_type || "受控数据源"}</p>
            <StatusPill value={item.status || "AVAILABLE"} />
          </article>
        ))}
        {!catalog.length && (
          <EmptyState
            title="暂无可用连接器"
            description="已批准的只读连接器目录为空，请先在平台管理中登记定义。"
          />
        )}
      </div>
      {createOpen && (
        <form className="data-card m7-form integration-flow" onSubmit={create}>
          <h2>创建只读集成</h2>
          <label>
            1. 选择连接器
            <select name="definition_id" required>
              <option value="">请选择</option>
              {catalog.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name || item.connector_type}
                </option>
              ))}
            </select>
          </label>
          <label>
            实例名称
            <input name="name" required />
          </label>
          <label>
            2. 数据源类型
            <select name="kind">
              <option value="FILESYSTEM">文件系统</option>
              <option value="S3">对象存储</option>
              <option value="WEB_REST">Web 服务</option>
              <option value="GIT">版本仓库</option>
            </select>
          </label>
          <label>
            3. 允许读取的范围（每行一个）
            <textarea name="allowlist" required />
          </label>
          <details className="technical-details">
            <summary>高级配置</summary>
            <div>
              <label>
                非敏感配置 JSON
                <textarea name="config" defaultValue="{}" required />
              </label>
            </div>
          </details>
          <button className="primary" type="submit">
            测试并保存
          </button>
        </form>
      )}
      <div className="data-card">
        <h2>已登记实例</h2>
        {loading ? (
          <p>正在读取已连接的数据源…</p>
        ) : items.length === 0 ? (
          <EmptyState
            title="还没有已连接的数据源"
            description="从上方连接器目录选择类型，完成权限范围和连接配置后保存。"
            primaryAction={
              <button
                type="button"
                className="primary"
                onClick={() => setCreateOpen(true)}
              >
                创建第一个集成
              </button>
            }
          />
        ) : (
          <ul className="stack-list">
            {items.map((item) => (
              <li key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <small>
                    {kindLabel(item.kind)} · <StatusPill value={item.status} />
                  </small>
                  <TechnicalDetails>
                    <pre>{JSON.stringify(item.watermark, null, 2)}</pre>
                  </TechnicalDetails>
                </div>
                <button
                  type="button"
                  disabled={Boolean(syncingId)}
                  onClick={() => void sync(item)}
                >
                  {syncingId === item.id ? "同步中…" : "开始同步"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {runs.length > 0 && (
        <div className="data-card">
          <h2>本次同步</h2>
          <ul className="stack-list">
            {runs.map((run) => (
              <li key={run.id}>
                <div>
                  <strong>
                    <StatusPill value={run.status} />
                  </strong>
                  <small>同步任务已记录</small>
                  <TechnicalDetails>
                    <code>
                      {run.workflow_id}
                      {run.error_code ? ` · ${run.error_code}` : ""}
                    </code>
                  </TechnicalDetails>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function kindLabel(value: string) {
  return (
    {
      FILESYSTEM: "文件系统",
      S3: "对象存储",
      WEB_REST: "Web 服务",
      GIT: "版本仓库",
    }[value] ?? value
  );
}
