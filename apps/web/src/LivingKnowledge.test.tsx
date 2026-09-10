import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { NexweaveApi } from "./api";
import { LivingKnowledge } from "./LivingKnowledge";
import type { ForecastRun, SignalBinding } from "./livingTypes";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function setup(status: string) {
  const api = new NexweaveApi("test");
  const binding: SignalBinding = {
    id: "binding",
    name: "合成绑定",
    entity_id: "entity",
    schema_version_id: "schema",
    source_version_id: "source",
    data_kind: "SYNTHETIC",
    operating_context: "合成回放",
    snapshot: {
      entity: { display_name: "演示对象" },
      signals: [
        {
          key: "temperature",
          displayName: "温度",
          unit: "degC",
          quantity: "temperature",
        },
      ],
      profile: {
        target: "temperature",
        pastCovariates: [],
        futureCovariates: [],
        frequencySeconds: 60,
        maxHorizon: 120,
      },
    },
  };
  const run: ForecastRun = {
    id: "run",
    status,
    artifact_id: null,
    error_code: null,
    delivery_status: "ACCEPTED",
    delivery_attempts: 1,
    delivery_error_code: null,
    retry_of: null,
    created_at: "2026-09-09T00:00:00Z",
    request: {
      binding_id: "binding",
      provider_id: "chronos2",
      horizon: 120,
      history_points: 720,
      scenario_name: "合成场景",
      future_paths: [],
    },
  };
  vi.spyOn(api, "signalBindings").mockResolvedValue({ items: [binding] });
  vi.spyOn(api, "forecastRuns").mockResolvedValue({ items: [run] });
  vi.spyOn(api, "wikiPages").mockResolvedValue({
    items: [],
  });
  vi.spyOn(api, "forecastRuntime").mockResolvedValue({
    worker_status: "UNAVAILABLE",
    worker_count: 0,
    queued: 1,
    running: 0,
    delivery_pending: 0,
    implementation_version: "0.9.5-a1",
  });
  render(
    <LivingKnowledge
      api={api}
      spaceId="space"
      view="wiki"
      onNavigate={vi.fn()}
    />,
  );
  return { api, run };
}

test("shows offline retention and immediately presents a cancelled result", async () => {
  const { api, run } = setup("QUEUED");
  const cancel = vi
    .spyOn(api, "forecastCommand")
    .mockResolvedValue({ ...run, status: "CANCELLED" });
  expect(await screen.findByText(/预测服务离线/)).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "取消本次预测" }));
  expect(await screen.findByText(/已停止结果发布/)).toBeInTheDocument();
  expect(cancel).toHaveBeenCalledWith(
    "run",
    "cancel",
    "用户取消本次预测",
    expect.any(String),
  );
});

test("network retry reuses command identity and selects the new immutable run", async () => {
  const { api, run } = setup("FAILED");
  const retry = vi
    .spyOn(api, "forecastCommand")
    .mockRejectedValueOnce(new Error("网络暂时不可用"))
    .mockResolvedValueOnce({
      ...run,
      id: "new-run",
      status: "QUEUED",
      retry_of: "run",
    });
  fireEvent.click(
    await screen.findByRole("button", { name: "以原输入重新运行" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "操作未能完成，请稍后重试。",
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "以原输入重新运行" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "以原输入重新运行" }));
  expect(
    await screen.findByText(/本次沿用原任务的冻结输入/),
  ).toBeInTheDocument();
  expect(retry.mock.calls[0][3]).toBe(retry.mock.calls[1][3]);
});
