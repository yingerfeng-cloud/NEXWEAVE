import {
  Component,
  type ErrorInfo,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { AdminPage } from "./AdminPage";
import { isDeveloperEnvironment, messageOf, NexweaveApi } from "./api";
import { CompileCenter } from "./CompileCenter";
import { AppShell, type NavigationItem } from "./design-system/AppShell";
import { PageHeader as PageTitle } from "./design-system/ui";
import { IntegrationCenter } from "./IntegrationCenter";
import { LivingKnowledge } from "./LivingKnowledge";
import { LoginPage } from "./LoginPage";
import {
  AskCenter,
  GraphCenter,
  QualityCenter,
  ReleaseCenter,
} from "./M7Knowledge";
import { OverviewPage } from "./OverviewPage";
import { PackCenter } from "./PackCenter";
import { ClaimCenter, ConflictCenter, ReviewCenter } from "./ReviewCenter";
import { SchemaStudio } from "./SchemaStudio";
import { SourceCenter } from "./SourceCenter";
import { SpacesPage } from "./SpacesPage";
import { TaskCenter } from "./TaskCenter";
import type { Principal, Role, Space } from "./types";
import { WikiLinkGraphCenter } from "./WikiLinkGraph";
import { WikiWorkbench } from "./WikiWorkbench";

const SESSION_KEY = "nexweave.m1.access-token";
const SPACE_KEY = "nexweave.m1.space";

const NAVIGATION: readonly NavigationItem[] = [
  { key: "overview", label: "总览", group: "工作台" },
  { key: "spaces", label: "知识空间", group: "工作台" },
  { key: "sources", label: "资料", group: "工作台" },
  { key: "tasks", label: "任务", group: "工作台" },
  { key: "compile", label: "编译", group: "工作台" },
  { key: "wiki", label: "Wiki", group: "知识建模" },
  { key: "schemas", label: "Schema Studio", group: "知识建模" },
  { key: "domain-packs", label: "领域包", group: "知识建模" },
  { key: "graph", label: "知识图谱", group: "知识建模" },
  { key: "claims", label: "主张与证据", group: "知识治理" },
  { key: "conflicts", label: "冲突", group: "知识治理" },
  { key: "reviews", label: "审核", group: "知识治理" },
  { key: "quality", label: "质量", group: "知识治理" },
  { key: "releases", label: "发布", group: "知识治理" },
  { key: "ask", label: "Ask NEXWEAVE", group: "智能使用" },
  { key: "integrations", label: "集成", group: "系统" },
  {
    key: "admin",
    label: "平台管理",
    group: "系统",
    adminOnly: true,
  },
] as const;

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY));
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [booting, setBooting] = useState(Boolean(token));
  const [locationKey, setLocationKey] = useState(readLocationKey);
  const route = locationKey.split(/[/?]/)[0] || "overview";
  const living =
    new URLSearchParams(locationKey.split("?")[1]).get("view") === "living";
  const livingRoutes = ["wiki", "graph", "ask", "schemas", "integrations"];
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [developerMode, setDeveloperMode] = useState(false);
  const [selectedSpaceId, setSelectedSpaceId] = useState(
    () => localStorage.getItem(SPACE_KEY) ?? "",
  );
  const [globalError, setGlobalError] = useState("");
  const api = useMemo(() => new NexweaveApi(token ?? undefined), [token]);

  const loadSpaces = useCallback(async () => {
    const result = await api.spaces();
    const visibleSpaces = developerMode
      ? result.items
      : result.items.filter((space) => !isDeveloperFixture(space));
    setSpaces(visibleSpaces);
    setSelectedSpaceId((current) => {
      const next = visibleSpaces.some((space) => space.id === current)
        ? current
        : (visibleSpaces[0]?.id ?? "");
      if (next) localStorage.setItem(SPACE_KEY, next);
      return next;
    });
  }, [api, developerMode]);

  useEffect(() => {
    const onPopState = () => setLocationKey(readLocationKey());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [locationKey]);

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
    history.pushState({}, "", `/${next.replace(/^\/+/, "")}`);
    setLocationKey(readLocationKey());
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
      <LoginPage
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
    <AppShell
      route={route}
      items={NAVIGATION}
      spaces={spaces}
      selectedSpaceId={selectedSpaceId}
      principal={principal}
      canAdmin={canAdmin}
      developerMode={developerMode}
      canToggleDeveloperMode={isDeveloperEnvironment()}
      error={globalError}
      onNavigate={navigate}
      onSelectSpace={selectSpace}
      onDismissError={() => setGlobalError("")}
      onLogout={logOut}
      onToggleDeveloperMode={() => setDeveloperMode((value) => !value)}
    >
      <AppErrorBoundary key={locationKey}>
        {livingRoutes.includes(route) && (
          <div className="living-switch" aria-label="知识视图">
            <button
              type="button"
              aria-pressed={!living}
              onClick={() => navigate(route)}
            >
              知识与治理
            </button>
            <button
              type="button"
              aria-pressed={living}
              onClick={() => navigate(`${route}?view=living`)}
            >
              运行与未来 · Chronos-2
            </button>
          </div>
        )}
        {living && livingRoutes.includes(route) && (
          <LivingKnowledge
            key={`${selectedSpaceId}:${route}`}
            api={api}
            spaceId={selectedSpaceId}
            view={route}
            onNavigate={navigate}
          />
        )}

        {route === "overview" && (
          <OverviewPage
            api={api}
            principal={principal}
            spaces={spaces}
            spaceId={selectedSpaceId}
            onNavigate={navigate}
          />
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
        {(route === "sources" || route === "source-versions") && (
          <SourceCenter
            api={api}
            principal={principal}
            spaceId={selectedSpaceId}
          />
        )}
        {route === "schemas" && !living && (
          <SchemaStudio api={api} spaceId={selectedSpaceId} />
        )}
        {route === "domain-packs" && (
          <PackCenter
            api={api}
            spaceId={selectedSpaceId}
            developerMode={developerMode}
          />
        )}
        {route === "compile" && (
          <CompileCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "tasks" && (
          <TaskCenter
            api={api}
            principal={principal}
            spaceId={selectedSpaceId}
          />
        )}
        {route === "wiki" && !living && (
          <WikiWorkbench
            api={api}
            spaceId={selectedSpaceId}
            onSelectPage={(pageId) =>
              navigate(`wiki?page=${encodeURIComponent(pageId)}`)
            }
          />
        )}
        {route === "claims" && (
          <ClaimCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "conflicts" && (
          <ConflictCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "reviews" && (
          <ReviewCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "quality" && (
          <QualityCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "releases" && (
          <ReleaseCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "ask" && !living && (
          <AskCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "graph" &&
          !living &&
          (new URLSearchParams(location.search).get("view") === "release" ? (
            <GraphCenter
              api={api}
              spaceId={selectedSpaceId}
              onShowWikiGraph={() => navigate("graph")}
            />
          ) : (
            <WikiLinkGraphCenter
              api={api}
              spaceId={selectedSpaceId}
              onOpenWikiPage={(pageId) =>
                navigate(`wiki?page=${encodeURIComponent(pageId)}`)
              }
              onShowReleaseGraph={() => navigate("graph?view=release")}
            />
          ))}
        {route === "integrations" && !living && (
          <IntegrationCenter api={api} spaceId={selectedSpaceId} />
        )}
        {route === "admin" &&
          (canAdmin ? (
            <AdminPage api={api} developerMode={developerMode} />
          ) : (
            <Denied />
          ))}
        {!NAVIGATION.some((item) => item.key === route) &&
          route !== "source-versions" && <NotFound />}
      </AppErrorBoundary>
    </AppShell>
  );
}

class AppErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    if (isDeveloperEnvironment())
      console.error("Page render failed", _error, _info);
  }

  render() {
    if (this.state.failed) {
      return (
        <section className="page">
          <div className="form-error" role="alert">
            页面暂时无法显示，请刷新后重试。
            <button type="button" onClick={() => location.reload()}>
              刷新
            </button>
          </div>
        </section>
      );
    }
    return this.props.children;
  }
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

function readLocationKey() {
  const path = location.pathname.replace(/^\//, "") || "overview";
  return `${path}${location.search}`;
}

function hasAnyRole(principal: Principal, ...roles: Role[]) {
  return roles.some((role) => principal.roles.includes(role));
}

function isDeveloperFixture(space: Space) {
  return /\bM\d+\b|\btest(?:[-_]|$)|E2E|isolat(?:ed|ion)|failure audit|technical pilot|阶段\s*A|stage-a/i.test(
    `${space.display_name} ${space.slug}`,
  );
}
