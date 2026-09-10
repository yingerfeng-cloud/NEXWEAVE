import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  act,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ForecastKnowledge } from "./ForecastKnowledge";
import { NexweaveApi } from "./api";
import type { ForecastKnowledgeContext } from "./livingTypes";
import type { KnowledgeRelease } from "./types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const reply = {
  items: [],
  explanation: "证据不足示例",
  limitations: [],
  checked_at: "2026-09-09T00:00:00Z",
} as unknown as ForecastKnowledgeContext;
function setup() {
  const api = new NexweaveApi("test");
  vi.spyOn(api, "releases").mockResolvedValue({
    items: [
      { id: "r1", version: "1.0.0", published_at: "2026-09-09T00:00:00Z" },
      { id: "r2", version: "2.0.0", published_at: "2026-09-09T00:00:00Z" },
    ] as KnowledgeRelease[],
  });
  return api;
}
test("requires explicit release and question, and clears prior evidence on edits", async () => {
  const api = setup();
  const search = vi.spyOn(api, "forecastKnowledge").mockResolvedValue(reply);
  render(
    <ForecastKnowledge
      api={api}
      spaceId="space"
      artifactId="artifact"
      onNavigate={vi.fn()}
    />,
  );
  const button = await screen.findByRole("button", { name: "检索已发布依据" });
  expect(button).toBeDisabled();
  fireEvent.change(screen.getByLabelText("固定知识版本"), {
    target: { value: "r1" },
  });
  fireEvent.change(screen.getByLabelText("查找什么依据"), {
    target: { value: "temperature" },
  });
  fireEvent.click(button);
  expect(await screen.findByText("证据不足示例")).toBeInTheDocument();
  expect(search).toHaveBeenCalledWith("artifact", "r1", "temperature");
  fireEvent.change(screen.getByLabelText("固定知识版本"), {
    target: { value: "r2" },
  });
  expect(screen.queryByText("证据不足示例")).not.toBeInTheDocument();
});
test("ignores response for an older question after input changes", async () => {
  const api = setup();
  let resolve!: (r: ForecastKnowledgeContext) => void;
  vi.spyOn(api, "forecastKnowledge").mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  render(
    <ForecastKnowledge
      api={api}
      spaceId="space"
      artifactId="artifact"
      onNavigate={vi.fn()}
    />,
  );
  await screen.findByRole("button", { name: "检索已发布依据" });
  fireEvent.change(screen.getByLabelText("固定知识版本"), {
    target: { value: "r1" },
  });
  fireEvent.change(screen.getByLabelText("查找什么依据"), {
    target: { value: "old" },
  });
  fireEvent.click(screen.getByRole("button", { name: "检索已发布依据" }));
  fireEvent.change(screen.getByLabelText("查找什么依据"), {
    target: { value: "new" },
  });
  await act(async () => resolve(reply));
  expect(screen.queryByText("证据不足示例")).not.toBeInTheDocument();
});
test("explains empty releases and permits retry after a failed load", async () => {
  const api = setup();
  vi.mocked(api.releases)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue({ items: [] });
  render(
    <ForecastKnowledge
      api={api}
      spaceId="space"
      artifactId="artifact"
      onNavigate={vi.fn()}
    />,
  );
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "重新加载版本" }));
  await waitFor(() =>
    expect(
      screen.getByText(/当前空间没有可用的已发布知识版本/),
    ).toBeInTheDocument(),
  );
});
