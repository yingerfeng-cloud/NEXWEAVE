import { useCallback, useEffect, useState, type FormEvent } from "react";

import { messageOf, NexweaveApi } from "./api";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  StatusPill,
  TechnicalDetails,
} from "./design-system/ui";
import type { WikiPage, WikiPageVersion } from "./types";

export function WikiWorkbench({
  api,
  spaceId,
  onSelectPage,
}: {
  api: NexweaveApi;
  spaceId: string;
  onSelectPage: (pageId: string) => void;
}) {
  const [pages, setPages] = useState<WikiPage[]>([]);
  const [selected, setSelected] = useState<WikiPage | null>(null);
  const [versions, setVersions] = useState<WikiPageVersion[]>([]);
  const [visibleVersion, setVisibleVersion] = useState<WikiPageVersion | null>(
    null,
  );
  const [protectedText, setProtectedText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [followBusy, setFollowBusy] = useState(false);

  const load = useCallback(async () => {
    if (!spaceId) {
      setPages([]);
      setSelected(null);
      setVersions([]);
      setVisibleVersion(null);
      setError("");
      return;
    }
    try {
      setPages((await api.wikiPages(spaceId)).items);
      setError("");
    } catch (cause) {
      setError(messageOf(cause, "无法读取 Wiki。"));
    }
  }, [api, spaceId]);

  useEffect(() => void load(), [load]);

  const open = useCallback(
    async (pageId: string) => {
      try {
        const [page, history] = await Promise.all([
          api.wikiPage(pageId),
          api.wikiPageVersions(pageId),
        ]);
        setSelected(page);
        setVersions(history.items);
        setVisibleVersion(page.current_version || history.items[0] || null);
        setProtectedText(
          JSON.stringify(
            page.current_version?.protected_sections || {},
            null,
            2,
          ),
        );
      } catch (cause) {
        setError(messageOf(cause, "无法读取页面。"));
      }
    },
    [api],
  );

  useEffect(() => {
    const requestedPageId = new URLSearchParams(location.search).get("page");
    if (
      requestedPageId &&
      pages.some((page) => page.id === requestedPageId) &&
      selected?.id !== requestedPageId
    ) {
      void open(requestedPageId);
    }
  }, [open, pages, selected?.id]);

  async function switchVersion(versionId: string) {
    if (!selected) return;
    try {
      setVisibleVersion(await api.wikiPageVersion(selected.id, versionId));
    } catch (cause) {
      setError(messageOf(cause, "无法切换版本。"));
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    try {
      const protected_sections = JSON.parse(protectedText) as Record<
        string,
        string
      >;
      const updated = await api.editWikiPage(selected, {
        protected_sections,
        reason: "Wiki 工作台人工保护区编辑",
      });
      await load();
      await open(updated.id);
    } catch (cause) {
      setError(messageOf(cause, "无法保存保护区。"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content-page">
      <PageHeader
        title="Wiki 工作台"
        description="浏览版本化知识页面、来源证据和反向链接；人工保护内容不会被自动改写。"
      />
      {error && <ErrorState message={error} onRetry={load} />}
      {!spaceId && (
        <EmptyState
          title="先选择知识空间"
          description="Wiki 工作台只展示当前知识空间的版本化页面。"
        />
      )}
      <div className="wiki-workspace">
        <aside className="data-card wiki-directory">
          <h2>页面目录</h2>
          {pages.map((page) => (
            <button
              className="list-row"
              key={page.id}
              type="button"
              onClick={() => onSelectPage(page.id)}
            >
              <strong title={page.title}>{page.title}</strong>
              <small>
                <StatusPill value={page.status} /> · v{page.version}
              </small>
            </button>
          ))}
          {!pages.length && (
            <EmptyState
              title="还没有 Wiki 页面"
              description="先在编译中心生成知识草稿；通过审核后，版本化页面会出现在这里。"
            />
          )}
        </aside>
        <section className="data-card wiki-document">
          {!selected || !visibleVersion ? (
            <EmptyState
              title="选择一个 Wiki 页面"
              description="在左侧目录选择页面，查看正文、版本和引用关系。"
            />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <h2>{selected.title}</h2>
                  <small>
                    {selected.template_key} · {selected.backlinks?.length || 0}{" "}
                    个反向引用
                  </small>
                </div>
                <button
                  type="button"
                  disabled={followBusy}
                  onClick={async () => {
                    setFollowBusy(true);
                    try {
                      await api.followWikiPage(selected.id, !selected.followed);
                      await open(selected.id);
                    } catch (cause) {
                      setError(messageOf(cause, "无法更新关注状态。"));
                    } finally {
                      setFollowBusy(false);
                    }
                  }}
                >
                  {followBusy
                    ? "保存中…"
                    : selected.followed
                      ? "取消关注"
                      : "关注"}
                </button>
              </div>
              <label>
                版本
                <select
                  value={visibleVersion.id}
                  onChange={(event) => void switchVersion(event.target.value)}
                >
                  {versions.map((version) => (
                    <option value={version.id} key={version.id}>
                      r{version.revision} · {statusLabel(version.status)} ·{" "}
                      {new Date(version.created_at).toLocaleString()}
                    </option>
                  ))}
                </select>
              </label>
              <article className="wiki-preview">
                <pre>{visibleVersion.markdown}</pre>
              </article>
              <TechnicalDetails summary="查看结构化属性">
                <pre>{JSON.stringify(visibleVersion.properties, null, 2)}</pre>
                <code>{visibleVersion.content_checksum}</code>
              </TechnicalDetails>
              {visibleVersion.id === selected.current_version_id && (
                <details className="technical-details">
                  <summary>高级编辑 · 人工保护区</summary>
                  <form className="m7-form" onSubmit={save}>
                    <label>
                      保护内容 JSON
                      <textarea
                        rows={8}
                        value={protectedText}
                        onChange={(event) =>
                          setProtectedText(event.target.value)
                        }
                      />
                    </label>
                    <button type="submit" disabled={busy}>
                      {busy ? "保存中…" : "创建人工编辑版本"}
                    </button>
                  </form>
                </details>
              )}
            </>
          )}
        </section>
        <aside className="data-card evidence-sidebar" aria-label="证据与版本">
          <h2>证据与版本</h2>
          {selected?.evidence_candidates?.length ? (
            selected.evidence_candidates.map((item, index) => (
              <article key={index} className="evidence-item">
                <strong>证据候选 {index + 1}</strong>
                <TechnicalDetails>
                  <pre>{JSON.stringify(item, null, 2)}</pre>
                </TechnicalDetails>
              </article>
            ))
          ) : (
            <EmptyState
              title="暂无证据候选"
              description="页面完成证据绑定后，来源和定位信息会显示在这里。"
            />
          )}
          {selected && <p>{selected.backlinks?.length || 0} 个反向链接</p>}
        </aside>
      </div>
    </section>
  );
}

function statusLabel(value: string) {
  return (
    {
      DRAFT: "草稿",
      PUBLISHED: "已发布",
      ARCHIVED: "已归档",
      SUPERSEDED: "已被替代",
    }[value] ?? value
  );
}
