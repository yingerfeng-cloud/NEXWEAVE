import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

const principal = {
  actor_type: "USER",
  actor_id: "0198d2d3-6c04-7000-8000-000000000001",
  tenant_id: "0198d2d3-6c04-7000-8000-000000000002",
  subject: "local-admin",
  roles: ["platform_admin", "tenant_admin"],
  clearance: "HIGHLY_RESTRICTED",
};

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  history.replaceState({}, "", "/overview");
  vi.stubGlobal("scrollTo", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("authenticates through the development identity provider and opens the M2 shell", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  expect(screen.getByRole("heading", { name: "进入平台" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "验证身份并进入" }));

  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: "平台总览" }),
    ).toBeInTheDocument(),
  );
  expect(screen.getAllByText("质量知识空间").length).toBeGreaterThan(0);
  expect(
    screen.getByRole("navigation", { name: "主导航" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /平台管理/ })).toBeEnabled();
  expect(sessionStorage.getItem("nexweave.m1.access-token")).toBe("test-token");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/auth/dev/session",
    expect.objectContaining({ method: "POST" }),
  );
});

test("restores a trusted session and opens the real M3 source center", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: "平台总览" }),
    ).toBeInTheDocument(),
  );
  expect(
    screen
      .getByRole("navigation", { name: "主导航" })
      .querySelectorAll("button"),
  ).toHaveLength(17);
  expect(screen.getByRole("button", { name: "任务" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "资料" }));
  expect(screen.getByRole("heading", { name: "资料中心" })).toBeInTheDocument();
  expect(await screen.findByText("当前知识空间还没有资料")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ 导入资料" })).toBeEnabled();
});

test("opens the real M5 compile center from a refresh-safe route", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/compile");
  vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "编译中心" }),
  ).toBeInTheDocument();
  expect(screen.getByText("选择知识版本")).toBeInTheDocument();
  expect(screen.getByText("前置条件检查")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始编译" })).toBeDisabled();
  expect(await screen.findByText("还没有编译记录")).toBeInTheDocument();
});

test("opens the real workflow task center and supports keyboard quick navigation", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/tasks");
  vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "任务中心" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("当前没有任务")).toBeInTheDocument();

  fireEvent.keyDown(window, { key: "k", ctrlKey: true });
  const quickNavigation = screen.getByRole("combobox", { name: "快速导航" });
  fireEvent.change(quickNavigation, { target: { value: "Schema" } });
  fireEvent.keyDown(quickNavigation, { key: "Enter" });

  expect(
    await screen.findByRole("heading", { name: "Schema Studio" }),
  ).toBeInTheDocument();
});

test("switches graph modes when only the query string changes", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/graph");
  vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "页面知识图谱" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "发布关系图" }));

  expect(
    await screen.findByRole("heading", { name: "关系图谱" }),
  ).toBeInTheDocument();
  expect(location.search).toBe("?view=release");

  fireEvent.click(screen.getByRole("button", { name: "查看页面知识图谱" }));
  expect(
    await screen.findByRole("heading", { name: "页面知识图谱" }),
  ).toBeInTheDocument();
  expect(location.search).toBe("");
});

test("persists the selected Wiki page in the refresh-safe URL", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/wiki");
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith(`/wiki/pages/${wikiPage.id}/versions`)) {
      return json({ items: [wikiVersion] });
    }
    if (url.endsWith(`/wiki/pages/${wikiPage.id}`)) return json(wikiPage);
    if (url.includes("/wiki/pages")) return json({ items: [wikiPage] });
    return mockApi(input, init);
  });
  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: /压缩机维护页/ }));

  expect(location.pathname).toBe("/wiki");
  expect(new URLSearchParams(location.search).get("page")).toBe(wikiPage.id);
  expect(await screen.findByText("受控 Wiki 正文")).toBeInTheDocument();
});

test("clears and restores task detail across task history locations", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/tasks");
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith(`/workflow-tasks/${workflowTask.id}`)) {
      return json({
        task: workflowTask,
        steps: [],
        events: [],
        allowed_actions: [],
      });
    }
    if (url.includes("/workflow-tasks")) return json({ items: [workflowTask] });
    return mockApi(input, init);
  });
  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: /受控测试任务/ }));
  expect(location.pathname).toBe(`/tasks/${workflowTask.id}`);
  expect(await screen.findByText(/run-test-001/)).toBeInTheDocument();

  history.pushState({}, "", "/tasks");
  window.dispatchEvent(new PopStateEvent("popstate"));
  expect(await screen.findByText("选择一个任务")).toBeInTheDocument();

  history.pushState({}, "", `/tasks/${workflowTask.id}`);
  window.dispatchEvent(new PopStateEvent("popstate"));
  expect(await screen.findByText(/run-test-001/)).toBeInTheDocument();
});

test("guards platform administration for a least-privilege consumer", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "consumer-token");
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith("/auth/me")) {
      return json({ ...principal, roles: ["consumer"] });
    }
    return mockApi(input, init);
  });
  render(<App />);

  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: "平台总览" }),
    ).toBeInTheDocument(),
  );
  expect(screen.getByRole("button", { name: /平台管理/ })).toBeDisabled();
  expect(screen.getByText("当前账号不可查看审计活动")).toBeInTheDocument();
});

test("shows a retryable authentication error instead of blanking the application", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({ code: "AUTHENTICATION_REQUIRED", detail: "身份不可用" }),
      { status: 401 },
    ),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "验证身份并进入" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "当前账号没有执行此操作的权限",
  );
  expect(screen.getByRole("button", { name: "验证身份并进入" })).toBeEnabled();
});

test("retries a failed audit projection without losing the authenticated shell", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  let auditCalls = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/audit-logs") && auditCalls++ === 0) {
      return json(
        { code: "DEPENDENCY_UNAVAILABLE", detail: "审计暂时不可用" },
        503,
      );
    }
    return mockApi(input, init);
  });
  render(<App />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "服务暂时不可用，请稍后重试",
  );
  fireEvent.click(screen.getByRole("button", { name: "重试" }));

  await waitFor(() =>
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
  );
  expect(screen.getByRole("heading", { name: "平台总览" })).toBeInTheDocument();
  expect(auditCalls).toBe(2);
});

async function mockApi(input: RequestInfo | URL, init?: RequestInit) {
  const url = String(input);
  if (url.endsWith("/auth/dev/session") && init?.method === "POST") {
    return json({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 900,
      principal,
    });
  }
  if (url.endsWith("/auth/me")) return json(principal);
  if (url.endsWith("/spaces")) {
    return json({
      items: [
        {
          id: "0198d2d3-6c04-7000-8000-000000000003",
          tenant_id: principal.tenant_id,
          organization_id: "0198d2d3-6c04-7000-8000-000000000004",
          slug: "quality",
          display_name: "质量知识空间",
          description: "真实测试空间",
          default_classification: "INTERNAL",
          status: "ACTIVE",
          version: 1,
          created_at: "2026-08-24T00:00:00Z",
          updated_at: "2026-08-24T00:00:00Z",
        },
      ],
    });
  }
  if (url.includes("/audit-logs")) return json({ items: [] });
  if (url.includes("/workflow-tasks")) return json({ items: [] });
  if (url.includes("/wiki-link-graph")) {
    return json({
      focus_page_id: null,
      max_depth: 2,
      node_limit: 180,
      truncated: false,
      nodes: [],
      edges: [],
    });
  }
  if (url.includes("/releases")) return json({ items: [] });
  if (url.includes("/claims")) return json({ items: [] });
  if (url.includes("/review-cases")) return json({ items: [] });
  if (url.includes("/conflicts")) return json({ items: [] });
  if (url.includes("/evaluation-suites")) return json({ items: [] });
  if (url.includes("/compile-jobs")) return json({ items: [] });
  if (url.includes("/schemas")) return json({ items: [] });
  if (url.endsWith("/prompt-versions")) return json({ items: [] });
  if (url.endsWith("/model-profiles")) return json({ items: [] });
  if (url.includes("/spaces/") && url.includes("/sources")) {
    return json({ items: [], next_cursor: null });
  }
  throw new Error(`Unexpected test API request: ${url}`);
}

const workflowTask = {
  id: "0198d2d3-6c04-7000-8000-000000000099",
  tenant_id: principal.tenant_id,
  space_id: "0198d2d3-6c04-7000-8000-000000000003",
  workflow_type: "KNOWLEDGE_COMPILE",
  business_key: "test-001",
  display_name: "受控测试任务",
  workflow_id: "workflow-test-001",
  temporal_run_id: "run-test-001",
  status: "RUNNING",
  version: 1,
  progress: 40,
  input_refs: {},
  result_summary: {},
  projection_revision: 1,
  projection_in_sync: true,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
};

const wikiVersion = {
  id: "0198d2d3-6c04-7000-8000-000000000088",
  wiki_page_id: "0198d2d3-6c04-7000-8000-000000000077",
  revision: 1,
  generated_sections: {},
  protected_sections: {},
  properties: {},
  markdown: "受控 Wiki 正文",
  content_checksum: "sha256:test",
  status: "DRAFT",
  created_at: "2026-09-01T00:00:00Z",
  created_by: principal.actor_id,
};

const wikiPage = {
  id: wikiVersion.wiki_page_id,
  tenant_id: principal.tenant_id,
  space_id: "0198d2d3-6c04-7000-8000-000000000003",
  schema_version_id: "0198d2d3-6c04-7000-8000-000000000066",
  primary_entity_id: "0198d2d3-6c04-7000-8000-000000000055",
  template_key: "equipment-page",
  slug: "compressor-maintenance",
  title: "压缩机维护页",
  status: "DRAFT",
  current_version_id: wikiVersion.id,
  current_version: wikiVersion,
  version: 1,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
  backlinks: [],
  followed: false,
};

function json(value: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}
