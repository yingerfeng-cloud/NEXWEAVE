import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "./App";

vi.mock("./LivingKnowledge", () => ({
  LivingKnowledge: ({ onNavigate }: { onNavigate: (path: string) => void }) => (
    <button
      onClick={() =>
        onNavigate("/source-versions/version/preview?anchor_id=anchor")
      }
    >
      查看原文定位
    </button>
  ),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  localStorage.clear();
});

test("opens a root-relative citation through the actual App and SourceCenter", async () => {
  sessionStorage.setItem("nexweave.m1.access-token", "test-token");
  history.replaceState({}, "", "/wiki?view=living");
  vi.stubGlobal("scrollTo", vi.fn());
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) => {
      const url = String(input);
      let body;
      if (url.endsWith("/auth/me"))
        body = { subject: "test", roles: ["consumer"], clearance: "INTERNAL" };
      else if (url.endsWith("/spaces"))
        body = { items: [{ id: "space", name: "test", status: "ACTIVE" }] };
      else if (url.includes("/source-versions/version/preview"))
        body = {
          sanitized_content: "Released source text",
          anchor_status: "VALID",
          locator_results: [],
          parse_job_id: "parse",
          content_type: "text/plain",
        };
      else throw new Error(`Unexpected test request: ${url}`);
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "查看原文定位" }));
  expect(
    await screen.findByRole("heading", { name: "安全原文预览" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Released source text")).toBeInTheDocument();
  expect(location.pathname + location.search).toBe(
    "/source-versions/version/preview?anchor_id=anchor",
  );
  expect(fetcher).toHaveBeenCalledWith(
    "/api/v1/source-versions/version/preview?anchor_id=anchor",
    expect.anything(),
  );
});
