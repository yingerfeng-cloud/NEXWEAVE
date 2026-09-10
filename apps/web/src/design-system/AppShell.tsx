import { useEffect, useRef, useState, type ReactNode } from "react";

import type { Principal, Space } from "../types";
import { Icon } from "./Icon";

export type NavigationItem = {
  key: string;
  label: string;
  group: "工作台" | "知识建模" | "知识治理" | "智能使用" | "系统";
  adminOnly?: boolean;
};

export function AppShell({
  route,
  items,
  spaces,
  selectedSpaceId,
  principal,
  canAdmin,
  developerMode,
  canToggleDeveloperMode,
  error,
  onNavigate,
  onSelectSpace,
  onDismissError,
  onLogout,
  onToggleDeveloperMode,
  children,
}: {
  route: string;
  items: readonly NavigationItem[];
  spaces: Space[];
  selectedSpaceId: string;
  principal: Principal;
  canAdmin: boolean;
  developerMode: boolean;
  canToggleDeveloperMode: boolean;
  error: string;
  onNavigate: (route: string) => void;
  onSelectSpace: (spaceId: string) => void;
  onDismissError: () => void;
  onLogout: () => void;
  onToggleDeveloperMode: () => void;
  children: ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeResult, setActiveResult] = useState(0);
  const searchRef = useRef<HTMLInputElement>(null);
  const selected = spaces.find((space) => space.id === selectedSpaceId);
  const activeRouteKey = route === "source-versions" ? "sources" : route;
  const activeItem = items.find((item) => item.key === activeRouteKey);
  const visibleItems = items.filter((item) => !item.adminOnly || canAdmin);
  const results = query.trim()
    ? visibleItems.filter((item) =>
        `${item.label} ${item.key}`.toLowerCase().includes(query.toLowerCase()),
      )
    : visibleItems;
  const groupedItems = (
    ["工作台", "知识建模", "知识治理", "智能使用", "系统"] as const
  ).map((group) => ({
    group,
    items: items.filter((item) => item.group === group),
  }));

  useEffect(() => {
    const openSearch = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
        setActiveResult(0);
        requestAnimationFrame(() => searchRef.current?.focus());
      }
      if (event.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", openSearch);
    return () => window.removeEventListener("keydown", openSearch);
  }, []);

  function choose(key: string) {
    setQuery("");
    setSearchOpen(false);
    setActiveResult(0);
    onNavigate(key);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          type="button"
          className="brand"
          aria-label="返回总览"
          onClick={() => onNavigate("overview")}
        >
          <span className="brand-mark">N</span>
          <span className="brand-copy">
            <strong>NEXWEAVE</strong>
            <small>Trusted Knowledge OS</small>
          </span>
        </button>
        <div className="space-picker">
          <label htmlFor="space-picker">当前知识空间</label>
          <div className="space-select-row">
            <span aria-hidden="true">
              {(selected?.display_name ?? "N").slice(0, 1).toUpperCase()}
            </span>
            <select
              id="space-picker"
              value={selectedSpaceId}
              title={selected?.display_name ?? "尚无空间"}
              onChange={(event) => onSelectSpace(event.target.value)}
            >
              {!spaces.length && <option value="">尚无空间</option>}
              {spaces.map((space) => (
                <option value={space.id} key={space.id}>
                  {space.display_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <label className="mobile-nav-picker" htmlFor="mobile-navigation">
          <span>当前页面</span>
          <select
            id="mobile-navigation"
            value={activeRouteKey}
            onChange={(event) => onNavigate(event.target.value)}
          >
            {groupedItems.map(({ group, items: groupItems }) => (
              <optgroup label={group} key={group}>
                {groupItems.map((item) => (
                  <option
                    value={item.key}
                    key={item.key}
                    disabled={Boolean(item.adminOnly && !canAdmin)}
                  >
                    {item.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <nav aria-label="主导航">
          {groupedItems.map(({ group, items: groupItems }) => {
            if (!groupItems.length || group === "系统") return null;
            return (
              <details className="nav-group" key={group} open>
                <summary>{group}</summary>
                <div>
                  {groupItems.map((item) => {
                    const disabled = Boolean(item.adminOnly && !canAdmin);
                    const active =
                      route === item.key ||
                      (item.key === "sources" && route === "source-versions");
                    return (
                      <button
                        type="button"
                        className={active ? "active" : ""}
                        aria-current={active ? "page" : undefined}
                        disabled={disabled}
                        key={item.key}
                        onClick={() => onNavigate(item.key)}
                      >
                        <Icon name={item.key} />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </details>
            );
          })}
          <div className="system-nav" role="group" aria-label="系统导航">
            <details className="nav-group" open>
              <summary>系统</summary>
              <div>
                {items
                  .filter((item) => item.group === "系统")
                  .map((item) => {
                    const active = route === item.key;
                    const disabled = Boolean(item.adminOnly && !canAdmin);
                    return (
                      <button
                        type="button"
                        className={active ? "active" : ""}
                        aria-current={active ? "page" : undefined}
                        disabled={disabled}
                        key={item.key}
                        onClick={() => onNavigate(item.key)}
                      >
                        <Icon name={item.key} />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
              </div>
            </details>
          </div>
        </nav>
        <div className="identity-card">
          <span className="avatar">
            {principal.subject.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{principal.subject}</strong>
            <small title={principal.roles.join(" · ")}>
              {principal.roles.map(roleLabel).join(" · ")}
            </small>
          </div>
          <button type="button" onClick={onLogout}>
            退出
          </button>
          {canToggleDeveloperMode && (
            <label className="developer-mode-toggle">
              <input
                type="checkbox"
                checked={developerMode}
                onChange={onToggleDeveloperMode}
              />
              开发信息
            </label>
          )}
        </div>
      </aside>
      <main className="workspace">
        <header className="workspace-header">
          <div className="workspace-context">
            <span>可信知识工作台</span>
            <strong>{activeItem?.label ?? "NEXWEAVE"}</strong>
          </div>
          <div
            className={`quick-nav ${searchOpen ? "is-open" : ""}`.trim()}
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget))
                setSearchOpen(false);
            }}
          >
            <button
              type="button"
              className="quick-nav-trigger"
              aria-label="打开快速导航"
              onClick={() => {
                setSearchOpen(true);
                setActiveResult(0);
                requestAnimationFrame(() => searchRef.current?.focus());
              }}
            >
              <Icon name="search" />
            </button>
            <label className={searchOpen ? "is-open" : ""}>
              <Icon name="search" />
              <input
                ref={searchRef}
                value={query}
                aria-label="快速导航"
                role="combobox"
                aria-expanded={searchOpen}
                aria-controls="quick-nav-options"
                aria-activedescendant={
                  searchOpen && results[activeResult]
                    ? `quick-nav-${results[activeResult].key}`
                    : undefined
                }
                placeholder="搜索页面或命令"
                onFocus={() => setSearchOpen(true)}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActiveResult(0);
                  setSearchOpen(true);
                }}
                onKeyDown={(event) => {
                  if (event.nativeEvent.isComposing) return;
                  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                    event.preventDefault();
                    setSearchOpen(true);
                    setActiveResult((current) =>
                      Math.max(
                        0,
                        Math.min(
                          Math.min(results.length, 8) - 1,
                          current + (event.key === "ArrowDown" ? 1 : -1),
                        ),
                      ),
                    );
                  }
                  if (event.key === "Enter" && results[activeResult])
                    choose(results[activeResult].key);
                }}
              />
              <kbd>⌘ K</kbd>
            </label>
            {searchOpen && (
              <div
                className="quick-nav-results"
                id="quick-nav-options"
                role="listbox"
                aria-label="页面"
              >
                {results.slice(0, 8).map((item, index) => (
                  <button
                    type="button"
                    id={`quick-nav-${item.key}`}
                    role="option"
                    aria-selected={index === activeResult}
                    key={item.key}
                    onClick={() => choose(item.key)}
                  >
                    {item.label}
                    <small>{item.group}</small>
                  </button>
                ))}
                {!results.length && <p>没有匹配的可达页面</p>}
              </div>
            )}
          </div>
          <span className="identity-status">
            <i />
            身份已验证
          </span>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            {error}
            <button type="button" onClick={onDismissError}>
              关闭
            </button>
          </div>
        )}
        <div className="content-region" onClick={() => setSearchOpen(false)}>
          {children}
        </div>
      </main>
    </div>
  );
}

function roleLabel(value: string) {
  return (
    {
      platform_admin: "平台管理员",
      tenant_admin: "组织管理员",
      space_admin: "空间管理员",
      knowledge_engineer: "知识工程师",
      reviewer: "审核员",
      publisher: "发布员",
      auditor: "审计员",
      consumer: "使用者",
    }[value] ?? "平台成员"
  );
}
