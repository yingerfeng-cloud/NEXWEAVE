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
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
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
  ).toHaveLength(16);

  fireEvent.click(screen.getByRole("button", { name: /资料中心/ }));
  expect(screen.getByRole("heading", { name: "资料中心" })).toBeInTheDocument();
  expect(
    await screen.findByText("当前空间尚无资料，可以从上方导入"),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "管理 Connector" })).toBeDisabled();
});

test("opens the real M2 task center from a refresh-safe route", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/compile");
  vi.spyOn(globalThis, "fetch").mockImplementation(mockApi);
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "任务中心" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Temporal 是执行权威/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "启动" })).toBeEnabled();
  expect(await screen.findByText("当前空间尚无工作流任务")).toBeInTheDocument();
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
  expect(screen.getByText("当前角色无审计查看权限")).toBeInTheDocument();
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

  expect(await screen.findByRole("alert")).toHaveTextContent("身份不可用");
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

  expect(await screen.findByRole("alert")).toHaveTextContent("审计暂时不可用");
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
  if (url.includes("/spaces/") && url.includes("/sources")) {
    return json({ items: [], next_cursor: null });
  }
  throw new Error(`Unexpected test API request: ${url}`);
}

function json(value: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}
