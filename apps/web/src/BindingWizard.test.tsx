import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { BindingWizard } from "./BindingWizard";
import { ApiError, NexweaveApi } from "./api";
import type { SchemaVersion, SourceDocument } from "./types";
import type { SignalBinding } from "./livingTypes";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("binds governed resources, invalidates edited precheck, and reuses save identity after network failure", async () => {
  const api = new NexweaveApi("test");
  const profile = {
    key: "test/profile",
    displayName: "温度预测",
    target: "test/temp",
    pastCovariates: [],
    futureCovariates: [],
    frequencySeconds: 60,
    maxHorizon: 120,
  };
  const signal = {
    key: "test/temp",
    displayName: "温度",
    typeKey: "test/type",
    unit: "degC",
    quantity: "temperature",
  };
  const schema = {
    id: "schema",
    schema_key: "test/schema",
    semantic_version: "1.0.0",
    status: "PUBLISHED",
    normalized_snapshot: {
      signalDefinitions: [signal],
      forecastProfiles: [profile],
    },
  } as unknown as SchemaVersion;
  const source = {
    id: "source",
    display_name: "合成 CSV",
    versions: [
      {
        id: "version",
        filename: "synthetic.csv",
        content_type: "text/csv",
        status: "PARSED",
        size: 4000,
        created_at: "2026-09-01T00:00:00Z",
      },
    ],
  } as unknown as SourceDocument;
  vi.spyOn(api, "schemas").mockResolvedValue({ items: [schema] });
  vi.spyOn(api, "bindingEntities").mockResolvedValue({
    items: [
      {
        id: "entity",
        display_name: "对象一",
        type_key: "test/type",
        schema_version_id: "schema",
      },
    ],
  });
  vi.spyOn(api, "sources").mockResolvedValue({ items: [source] });
  vi.spyOn(api, "source").mockResolvedValue(source);
  vi.spyOn(api, "csvBindingPreview").mockResolvedValue({
    source_version_id: "version",
    checksum: "hash",
    columns: ["time", "temp"],
    sample_rows: [{ time: "2026-09-01T00:00:00Z", temp: "45" }],
    row_count: 40,
  });
  const result = {
    valid: true as const,
    point_count: 40,
    start: "2026-09-01T00:00:00Z",
    end: "2026-09-01T00:39:00Z",
    latest_values: { "test/temp": 45 },
    source_checksum: "hash",
  };
  const validate = vi.spyOn(api, "validateBinding").mockResolvedValue(result);
  const saved = {
    id: "binding",
    name: "演示绑定",
    entity_id: "entity",
    schema_version_id: "schema",
    source_version_id: "version",
    data_kind: "SYNTHETIC",
    operating_context: "合成稳态",
    snapshot: {
      entity: { display_name: "对象一" },
      signals: [signal],
      profile,
    },
  } satisfies SignalBinding;
  const save = vi
    .spyOn(api, "createBinding")
    .mockRejectedValueOnce(
      new ApiError("连接中断", 503, "DEPENDENCY_UNAVAILABLE"),
    )
    .mockResolvedValue(saved);
  const done = vi.fn();
  render(
    <BindingWizard
      api={api}
      spaceId="space"
      onCreated={done}
      onClose={vi.fn()}
      onNavigate={vi.fn()}
    />,
  );
  await screen.findByRole("option", { name: "合成 CSV" });
  const choose = (label: string, value: string) =>
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  choose("CSV 资料", "source");
  await screen.findByRole("option", { name: /synthetic.csv/ });
  choose("已解析的资料版本", "version");
  choose("已发布时序模型", "schema");
  choose("预测配置", "test/profile");
  choose("知识对象", "entity");
  await screen.findByText(/共 40 行/);
  choose("时间列", "time");
  choose("温度的数据列", "temp");
  choose("温度的原始单位", "degC");
  choose("绑定名称", "演示绑定");
  choose("运行工况说明", "合成稳态");
  choose("数据性质", "SYNTHETIC");
  fireEvent.click(screen.getByRole("button", { name: "验证绑定与数据" }));
  await screen.findByText(/预检通过/);
  expect(validate.mock.calls[0][1].columns).toEqual([
    { signal_key: "test/temp", column: "temp", unit: "degC" },
  ]);
  choose("绑定名称", "新的绑定名称");
  expect(screen.getByRole("button", { name: "保存绑定" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "验证绑定与数据" }));
  await screen.findByText(/预检通过/);
  fireEvent.click(screen.getByRole("button", { name: "保存绑定" }));
  await screen.findByRole("alert");
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "保存绑定" })).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "保存绑定" }));
  await waitFor(() => expect(done).toHaveBeenCalledWith(saved, result));
  expect(save.mock.calls[0][2]).toBe(save.mock.calls[1][2]);
});
