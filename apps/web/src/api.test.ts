import { afterEach, expect, test, vi } from "vitest";

import { NexweaveApi } from "./api";
import type {
  ParseJob,
  SourceDocument,
  SourceUploadSession,
  SourceVersion,
} from "./types";

afterEach(() => vi.restoreAllMocks());

test("uploads controlled bytes and completes the exact approved session path", async () => {
  const api = new NexweaveApi("test-token");
  const session: SourceUploadSession = {
    id: "upload-1",
    tenant_id: "tenant-1",
    space_id: "space-1",
    source_document_id: "source-1",
    source_version_id: "version-1",
    import_batch_id: null,
    filename: "manual.txt",
    content_type: "text/plain",
    expected_size: 6,
    expected_checksum: `sha256:${"a".repeat(64)}`,
    object_key: `raw/v1/tenant/space/source/version/${"a".repeat(64)}`,
    status: "INITIATED",
    version: 1,
    upload_url: "/api/v1/sources/uploads/upload-1/content",
    expires_at: "2026-08-26T02:00:00Z",
    created_at: "2026-08-26T01:00:00Z",
  };
  const result = {
    source_id: "source-1",
    source_version_id: "version-1",
    parse_job_id: "parse-1",
    workflow_id: "source-ingestion/tenant/parse-1",
    run_id: "run-1",
    duplicate_source_version_ids: [],
    source_status: "ACTIVE",
    version_status: "PARSING",
  };
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(session)))
    .mockResolvedValueOnce(new Response(JSON.stringify(result)));
  const file = new File(["manual"], "manual.txt", { type: "text/plain" });

  await api.uploadSourceContent(session, file);
  await api.completeSourceUpload(
    session.id,
    session.expected_checksum,
    session.expected_size,
  );

  expect(fetchMock.mock.calls[0][0]).toBe(
    "/api/v1/sources/uploads/upload-1/content",
  );
  expect(fetchMock.mock.calls[0][1]).toEqual(
    expect.objectContaining({ method: "PUT", body: file }),
  );
  expect(
    new Headers(fetchMock.mock.calls[0][1]?.headers).get("Content-Type"),
  ).toBe("text/plain");
  expect(fetchMock.mock.calls[1][0]).toBe(
    "/api/v1/sources/uploads/upload-1/complete",
  );
  expect(fetchMock.mock.calls[1][1]).toEqual(
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        checksum: session.expected_checksum,
        size: session.expected_size,
      }),
    }),
  );
});

test("sends strong ETags for archive, reparse, retry and invalidation commands", async () => {
  const api = new NexweaveApi("test-token");
  const source = { id: "source-1", version: 7 } as SourceDocument;
  const version = { id: "version-1", version: 11 } as SourceVersion;
  const job = { id: "parse-1", version: 13 } as ParseJob;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({
          id: "result-1",
          version: 14,
          failure_units: [],
        }),
      ),
    ),
  );

  await api.archiveSource(source);
  await api.reparseSourceVersion(version, {
    parser_id: "nexweave.parser.builtin",
    parser_version: "1.0.0",
    config: {},
  });
  await api.retryParseJob(job);
  await api.invalidateSourceVersion(version, {
    reason_code: "SOURCE_WITHDRAWN",
    reason: "资料已撤回",
    policy_version: "m3.ui.v1",
  });

  expect(etag(fetchMock.mock.calls[0][1])).toBe('"v7"');
  expect(etag(fetchMock.mock.calls[1][1])).toBe('"v11"');
  expect(etag(fetchMock.mock.calls[2][1])).toBe('"v13"');
  expect(etag(fetchMock.mock.calls[3][1])).toBe('"v11"');
  for (const [, init] of fetchMock.mock.calls) {
    expect(new Headers(init?.headers).get("Idempotency-Key")).toBeTruthy();
  }
});

function etag(init?: RequestInit) {
  return new Headers(init?.headers).get("If-Match");
}
