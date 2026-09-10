import { useCallback, useEffect, useState, type FormEvent } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type { CompositionReport, SchemaVersion } from "./types";

export function SchemaStudio({
  api,
  spaceId,
}: {
  api: NexweaveApi;
  spaceId: string;
}) {
  const [items, setItems] = useState<SchemaVersion[]>([]);
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [snapshotText, setSnapshotText] = useState("{}");
  const [error, setError] = useState("");
  const [report, setReport] = useState<CompositionReport | null>(null);
  const [selected, setSelected] = useState<SchemaVersion | null>(null);
  const [working, setWorking] = useState("");

  const load = useCallback(async () => {
    if (!spaceId) {
      setItems([]);
      setSelected(null);
      setReport(null);
      setError("");
      return;
    }
    try {
      const nextItems = (await api.schemas(spaceId)).items;
      setItems(nextItems);
      setSelected((current) =>
        current && nextItems.some((item) => item.id === current.id)
          ? current
          : (nextItems[0] ?? null),
      );
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取知识模型。"));
    }
  }, [api, spaceId]);
  useEffect(() => {
    void load();
  }, [load]);
  async function create(event: FormEvent) {
    event.preventDefault();
    if (working) return;
    setWorking("create");
    try {
      const snapshot = JSON.parse(snapshotText) as Record<string, unknown>;
      await api.createSchema(spaceId, {
        schema_key: key,
        display_name: name,
        snapshot,
      });
      setKey("");
      setName("");
      await load();
    } catch (cause) {
      setError(messageOf(cause, "无法创建知识模型。"));
    } finally {
      setWorking("");
    }
  }
  async function validate(item: SchemaVersion) {
    if (working) return;
    setWorking(item.id);
    try {
      setReport(await api.validateSchema(item));
      setSelected(item);
      await load();
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "验证失败。"));
    } finally {
      setWorking("");
    }
  }
  async function publish(item: SchemaVersion) {
    if (working) return;
    setWorking(item.id);
    try {
      await api.publishSchema(item);
      await load();
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "发布失败。"));
    } finally {
      setWorking("");
    }
  }
  return (
    <section className="content-page">
      <PageHeader
        title="Schema Studio"
        description="以版本化知识模型定义对象、属性与关系；已发布版本保持不可变。"
      />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="Schema Studio 只展示当前知识空间的版本化模型。"
        />
      )}
      <div className="studio-layout">
        <aside className="data-card studio-list">
          <h2>知识模型</h2>
          {items.map((item) => (
            <button
              className={
                selected?.id === item.id ? "list-row selected" : "list-row"
              }
              key={item.id}
              type="button"
              onClick={() => setSelected(item)}
            >
              <strong title={item.schema_key}>{item.schema_key}</strong>
              <small>{item.semantic_version}</small>
              <StatusPill value={item.status} />
            </button>
          ))}
          {!items.length && (
            <EmptyState
              title="还没有知识模型"
              description="创建第一个模型，定义知识对象、属性和关系。"
            />
          )}
        </aside>
        <div className="studio-editor">
          <form className="data-card m7-form" onSubmit={create}>
            <h2>创建模型草稿</h2>
            <div className="form-grid two">
              <label>
                稳定标识
                <input
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  placeholder="example.org/equipment"
                  required
                />
                <small>发布后用于持续识别同一个知识模型。</small>
              </label>
              <label>
                模型名称
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </label>
            </div>
            <details className="technical-details">
              <summary>高级设置 · Source View</summary>
              <div>
                <label>
                  模型声明 JSON
                  <textarea
                    value={snapshotText}
                    onChange={(e) => setSnapshotText(e.target.value)}
                    rows={8}
                  />
                </label>
              </div>
            </details>
            <button
              className="primary"
              type="submit"
              disabled={Boolean(working)}
            >
              {working === "create" ? "创建中…" : "创建草稿"}
            </button>
          </form>
          <div className="data-card">
            <h2>版本历史</h2>
            {!items.length ? (
              <EmptyState
                title="暂无版本"
                description="创建模型草稿后，验证和发布状态会显示在这里。"
              />
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Key</th>
                    <th>版本</th>
                    <th>状态</th>
                    <th>组合校验</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <button
                          className="link-button"
                          type="button"
                          title={item.schema_key}
                          onClick={() => setSelected(item)}
                        >
                          {item.schema_key}
                        </button>
                      </td>
                      <td>{item.semantic_version}</td>
                      <td>
                        <StatusPill value={item.status} />
                        {item.breaking_change && (
                          <StatusPill value="BREAKING" tone="danger" />
                        )}
                      </td>
                      <td>
                        <code>{item.composition_checksum.slice(0, 20)}…</code>
                      </td>
                      <td>
                        <button
                          type="button"
                          disabled={Boolean(working) || item.status !== "DRAFT"}
                          onClick={() => void validate(item)}
                        >
                          验证
                        </button>
                        <button
                          type="button"
                          disabled={
                            Boolean(working) ||
                            item.status !== "TESTING" ||
                            item.breaking_change
                          }
                          onClick={() => void publish(item)}
                        >
                          发布
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
      {selected && (
        <div className="data-card">
          <h2>语义模型 · {selected.schema_key}</h2>
          <p>
            类型、属性、层级、关系、术语、映射与来源领域包均来自此版本快照。
          </p>
          <TechnicalDetails summary="查看模型源数据">
            <pre>{JSON.stringify(selected.normalized_snapshot, null, 2)}</pre>
          </TechnicalDetails>
        </div>
      )}
      {report && (
        <div className="data-card">
          <h2>组合报告</h2>
          <p>
            <code>{report.result_checksum}</code>
          </p>
          <TechnicalDetails summary="查看组合报告详情">
            <pre>{JSON.stringify(report.report, null, 2)}</pre>
          </TechnicalDetails>
        </div>
      )}
    </section>
  );
}
