import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { NexweaveApi } from "./api";
import { SourceCenter } from "./SourceCenter";
import type { Principal, SourceVersion } from "./types";

const principal: Principal = {
  actor_type: "USER",
  actor_id: "0198d2d3-6c04-7000-8000-000000000001",
  tenant_id: "0198d2d3-6c04-7000-8000-000000000002",
  subject: "source-engineer",
  roles: ["knowledge_engineer"],
  clearance: "HIGHLY_RESTRICTED",
};

beforeEach(() => {
  history.replaceState({}, "", "/sources");
  vi.stubGlobal("scrollTo", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("recovers a failed list and persists server-side filters in the URL", async () => {
  let calls = 0;
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/spaces/space-1/sources")) {
        calls += 1;
        if (calls === 1)
          return json(
            { code: "DEPENDENCY_UNAVAILABLE", detail: "资料目录暂时不可用" },
            503,
          );
        return json({ items: [], next_cursor: null });
      }
      throw new Error(`Unexpected request: ${url}`);
    });

  renderSourceCenter();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "资料目录暂时不可用",
  );
  fireEvent.click(screen.getByRole("button", { name: "重试" }));
  expect(
    await screen.findByText("当前空间尚无资料，可以从上方导入"),
  ).toBeInTheDocument();

  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "规范" },
  });
  fireEvent.change(screen.getByLabelText("文件类型"), {
    target: { value: "application/pdf" },
  });
  fireEvent.change(screen.getByLabelText("资料状态"), {
    target: { value: "ACTIVE" },
  });
  fireEvent.change(screen.getByLabelText("筛选密级"), {
    target: { value: "CONFIDENTIAL" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用筛选" }));

  await waitFor(() => expect(calls).toBe(3));
  expect(location.search).toContain("search=%E8%A7%84%E8%8C%83");
  const finalUrl = String(fetchMock.mock.calls.at(-1)?.[0]);
  expect(finalUrl).toContain("content_type=application%2Fpdf");
  expect(finalUrl).toContain("status=ACTIVE");
  expect(finalUrl).toContain("classification=CONFIDENTIAL");
});

test("restores a preview deep link and makes unresolved locators explicit", async () => {
  history.replaceState(
    {},
    "",
    "/source-versions/version-1/preview?anchor_id=anchor-1",
  );
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/source-versions/version-1/preview?anchor_id=anchor-1")) {
      return json({
        source_version_id: "version-1",
        parse_job_id: "parse-1",
        anchor_id: "anchor-1",
        anchor_status: "UNRESOLVED",
        content_type: "text/plain",
        sanitized_content: "<script>不会执行</script>\n净化正文",
        locator_results: [
          {
            locator: { kind: "page", page: 3 },
            matched: false,
            safe_detail: "not found",
          },
        ],
      });
    }
    throw new Error(`Unexpected request: ${url}`);
  });

  renderSourceCenter();
  expect(
    await screen.findByRole("heading", { name: "安全原文预览" }),
  ).toBeInTheDocument();
  expect(screen.getByText("UNRESOLVED")).toBeInTheDocument();
  expect(screen.getByText("未命中")).toBeInTheDocument();
  expect(screen.getByText("page 3")).toBeInTheDocument();
  expect(screen.getByText(/<script>不会执行<\/script>/)).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
});

test("shows active versus latest parse and preserves OCR_REQUIRED partial detail", async () => {
  history.replaceState(
    {},
    "",
    "/sources/source-1/versions/version-1?tab=parse",
  );
  const version: SourceVersion = {
    id: "version-1",
    tenant_id: principal.tenant_id,
    space_id: "space-1",
    source_document_id: "source-1",
    filename: "scanned.pdf",
    content_type: "application/pdf",
    size: 4096,
    checksum: `sha256:${"a".repeat(64)}`,
    object_version_id: "object-v1",
    classification: "INTERNAL",
    status: "PARTIAL",
    version: 4,
    active_parse_job_id: "parse-active",
    latest_parse_job_id: "parse-latest",
    supersedes_source_version_id: null,
    created_at: "2026-08-26T01:00:00Z",
    created_by: principal.actor_id,
  };
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/sources/source-1/versions/version-1"))
      return json(version);
    if (url.endsWith("/parse-jobs/parse-active"))
      return json(parseJob("parse-active", "SUCCEEDED", []));
    if (url.endsWith("/parse-jobs/parse-latest"))
      return json(
        parseJob("parse-latest", "PARTIAL_FAILED", [
          {
            id: "failure-1",
            parse_job_id: "parse-latest",
            error_code: "OCR_REQUIRED",
            scope: "page",
            scope_ref: "page:2",
            retryable: true,
            safe_detail: "扫描页没有可提取文本，且未配置 OCR Provider。",
          },
        ]),
      );
    if (url.includes("/source-versions/version-1/segments"))
      return json({ items: [], next_cursor: null });
    throw new Error(`Unexpected request: ${url}`);
  });

  renderSourceCenter();
  expect(await screen.findByText("OCR_REQUIRED")).toBeInTheDocument();
  expect(screen.getByText("PARTIAL_FAILED")).toBeInTheDocument();
  expect(screen.getByText(/未配置 OCR Provider/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试同一配置" })).toBeEnabled();
  expect(screen.getByText("ACTIVE PARSEJOB")).toBeInTheDocument();
  expect(screen.getByText("LATEST PARSEJOB")).toBeInTheDocument();
});

function renderSourceCenter() {
  return render(
    <SourceCenter
      api={new NexweaveApi("test-token")}
      principal={principal}
      spaceId="space-1"
    />,
  );
}

function parseJob(id: string, status: string, failureUnits: unknown[]) {
  return {
    id,
    tenant_id: principal.tenant_id,
    space_id: "space-1",
    source_version_id: "version-1",
    status,
    version: 3,
    parser_id: "nexweave.parser.builtin",
    parser_version: "1.0.0",
    config_checksum: `sha256:${"b".repeat(64)}`,
    document_model_version: "1.0",
    locator_version: "1.0",
    ocr_provider_id: null,
    ocr_provider_version: null,
    workflow_id: `source-ingestion/tenant/${id}`,
    temporal_run_id: `run-${id}`,
    result_checksum: null,
    failure_units: failureUnits,
    created_at: "2026-08-26T01:00:00Z",
    updated_at: "2026-08-26T01:01:00Z",
  };
}

function json(value: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}
