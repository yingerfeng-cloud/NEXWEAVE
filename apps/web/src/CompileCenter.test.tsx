import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import type { NexweaveApi } from "./api";
import { CompileCenter } from "./CompileCenter";
import type { SourceDocument } from "./types";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test("shows parsed versions returned by the source-list contract", async () => {
  const source = {
    id: "source-1",
    display_name: "Pump A maintenance record",
    versions: [
      {
        id: "version-1",
        source_document_id: "source-1",
        filename: "pump-a.txt",
        status: "PARSED",
      },
    ],
  } as unknown as SourceDocument;
  const api = {
    compileJobs: vi.fn().mockResolvedValue({ items: [] }),
    schemas: vi.fn().mockResolvedValue({ items: [] }),
    sources: vi.fn().mockResolvedValue({
      items: [source],
      next_cursor: null,
    }),
    executionOptions: vi
      .fn()
      .mockResolvedValue({ model_profiles: [], prompt_versions: [] }),
  } as unknown as NexweaveApi;

  render(<CompileCenter api={api} spaceId="space-1" />);

  const checkbox = await screen.findByRole("checkbox");
  expect(checkbox).toBeInTheDocument();
  expect(
    screen.getByLabelText(/Pump A maintenance record/),
  ).toBeInTheDocument();
  expect(screen.queryByText("没有可编译的资料")).not.toBeInTheDocument();
});

test("keeps parsed versions visible when an unrelated compile resource fails", async () => {
  const source = {
    id: "source-1",
    display_name: "Pump A maintenance record",
    versions: [
      {
        id: "version-1",
        source_document_id: "source-1",
        filename: "pump-a.txt",
        status: "PARSED",
      },
    ],
  } as unknown as SourceDocument;
  const api = {
    compileJobs: vi.fn().mockRejectedValue(new TypeError("offline")),
    schemas: vi.fn().mockResolvedValue({ items: [] }),
    sources: vi.fn().mockResolvedValue({ items: [source], next_cursor: null }),
    executionOptions: vi
      .fn()
      .mockResolvedValue({ model_profiles: [], prompt_versions: [] }),
  } as unknown as NexweaveApi;

  render(<CompileCenter api={api} spaceId="space-1" />);

  expect(await screen.findByRole("checkbox")).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("部分编译资源");
  expect(screen.queryByText("没有可编译的资料")).not.toBeInTheDocument();
});

function readyApi() {
  return {
    compileJobs: vi.fn().mockResolvedValue({ items: [] }),
    schemas: vi.fn().mockResolvedValue({
      items: [
        {
          id: "schema-1",
          status: "PUBLISHED",
          schema_key: "model",
          semantic_version: "1",
        },
      ],
    }),
    sources: vi.fn().mockResolvedValue({
      items: [
        {
          id: "source-1",
          display_name: "Old space source",
          versions: [{ id: "version-1", status: "PARSED" }],
        },
      ],
    }),
    executionOptions: vi.fn().mockResolvedValue({
      model_profiles: [{ id: "config-1", name: "Config" }],
      prompt_versions: [{ id: "config-1", prompt_key: "prompt" }],
    }),
    createCompileJob: vi.fn(),
  };
}

test("switching spaces clears selections and prevents submission while loading or unavailable", async () => {
  const api = readyApi();
  const { rerender, container } = render(
    <CompileCenter api={api as unknown as NexweaveApi} spaceId="space-1" />,
  );
  fireEvent.click(await screen.findByRole("checkbox"));
  let rejectNext!: (reason: Error) => void;
  api.sources.mockImplementationOnce(
    () =>
      new Promise((_, reject) => {
        rejectNext = reject;
      }),
  );
  rerender(
    <CompileCenter api={api as unknown as NexweaveApi} spaceId="space-2" />,
  );
  expect(screen.queryByText(/Old space source/)).not.toBeInTheDocument();
  fireEvent.submit(container.querySelector("form")!);
  expect(api.createCompileJob).not.toHaveBeenCalled();
  await act(async () => rejectNext(new Error("unavailable")));
  expect(await screen.findByText("暂时无法读取资料版本")).toBeInTheDocument();
  fireEvent.submit(container.querySelector("form")!);
  expect(api.createCompileJob).not.toHaveBeenCalled();
});

test("refresh failure clears previously selected sources", async () => {
  const api = readyApi();
  api.compileJobs.mockRejectedValue(new Error("jobs unavailable"));
  const { container } = render(
    <CompileCenter api={api as unknown as NexweaveApi} spaceId="space-1" />,
  );
  fireEvent.click(await screen.findByRole("checkbox"));
  api.sources.mockRejectedValueOnce(new Error("source unavailable"));
  fireEvent.click(screen.getByRole("button", { name: /重试/ }));
  expect(await screen.findByText("暂时无法读取资料版本")).toBeInTheDocument();
  expect(screen.queryByText(/Old space source/)).not.toBeInTheDocument();
  fireEvent.submit(container.querySelector("form")!);
  expect(api.createCompileJob).not.toHaveBeenCalled();
});

test("keeps parsed versions visible while the polling refresh is pending", async () => {
  vi.useFakeTimers();
  const api = readyApi();
  const { unmount } = render(
    <CompileCenter api={api as unknown as NexweaveApi} spaceId="space-1" />,
  );
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
  expect(screen.getByRole("checkbox")).toBeInTheDocument();

  let resolveRefresh!: (value: { items: SourceDocument[] }) => void;
  api.sources.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveRefresh = resolve;
      }),
  );

  await act(async () => {
    vi.advanceTimersByTime(3000);
    await Promise.resolve();
  });

  expect(screen.getByRole("checkbox")).toBeInTheDocument();

  await act(async () => {
    resolveRefresh({
      items: [
        {
          id: "source-1",
          display_name: "Old space source",
          versions: [{ id: "version-1", status: "PARSED" }],
        } as unknown as SourceDocument,
      ],
    });
    await Promise.resolve();
  });

  unmount();
});
