import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(cleanup);

import type { NexweaveApi } from "./api";
import { AskCenter, GraphCenter } from "./M7Knowledge";

const release = {
  id: "018f0000-0000-7000-8000-000000000001",
  space_id: "018f0000-0000-7000-8000-000000000002",
  candidate_id: "018f0000-0000-7000-8000-000000000003",
  version: "1.0.0",
  status: "PUBLISHED",
  manifest_checksum: `sha256:${"a".repeat(64)}`,
  schema_version_id: "018f0000-0000-7000-8000-000000000004",
  model_profile_id: "018f0000-0000-7000-8000-000000000005",
  prompt_version_id: "018f0000-0000-7000-8000-000000000006",
  published_at: "2026-08-31T00:00:00Z",
};

describe("M7 trusted consumption pages", () => {
  it("discards graph responses after a Release switch", async () => {
    let finish!: (value: unknown) => void;
    const graphTraverse = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const api = {
      releases: vi.fn().mockResolvedValue({
        items: [
          release,
          { ...release, id: "second-release", version: "2.0.0" },
        ],
      }),
      graphTraverse,
    } as unknown as NexweaveApi;
    render(<GraphCenter api={api} spaceId={release.space_id} />);
    await screen.findByText("2.0.0");
    fireEvent.change(screen.getByPlaceholderText("输入实体标识"), {
      target: { value: "entity" },
    });
    fireEvent.click(screen.getByRole("button", { name: "遍历三跳" }));
    expect(screen.getByRole("button", { name: "遍历三跳" })).toBeDisabled();
    fireEvent.change(screen.getByRole("combobox", { name: "发布版本" }), {
      target: { value: "second-release" },
    });
    await act(async () =>
      finish({ nodes: [{ id: "entity" }], edges: [], truncated: false }),
    );
    expect(screen.queryByText("1 节点 · 0 关系")).not.toBeInTheDocument();
    expect(screen.getByText("选择起点开始探索")).toBeInTheDocument();
  });

  it("blocks duplicate submissions and discards an answer after changing Release", async () => {
    let finish!: (value: unknown) => void;
    const askRelease = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const api = {
      releases: vi.fn().mockResolvedValue({
        items: [
          release,
          { ...release, id: "second-release", version: "2.0.0" },
        ],
      }),
      askRelease,
    } as unknown as NexweaveApi;
    render(<AskCenter api={api} spaceId={release.space_id} />);
    await screen.findByText("2.0.0");
    fireEvent.change(screen.getByPlaceholderText("向当前发布提问…"), {
      target: { value: "   " },
    });
    expect(screen.getByRole("button", { name: "发送问题" })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("向当前发布提问…"), {
      target: { value: "证据？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(screen.getByRole("button", { name: "查询中…" })).toBeDisabled();
    fireEvent.submit(
      screen.getByPlaceholderText("向当前发布提问…").closest("form")!,
    );
    expect(askRelease).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByRole("combobox", { name: "当前发布" }), {
      target: { value: "second-release" },
    });
    await act(async () =>
      finish({
        release_id: release.id,
        question: "证据？",
        status: "REFUSED",
        direct_answer: "不应显示的旧结果",
        citations: [],
      }),
    );
    expect(screen.queryByText("不应显示的旧结果")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送问题" })).toBeEnabled();
  });

  it("renders an explicit evidence refusal returned by the fixed Release API", async () => {
    const api = {
      releases: vi.fn().mockResolvedValue({ items: [release] }),
      askRelease: vi.fn().mockResolvedValue({
        id: "018f0000-0000-7000-8000-000000000007",
        release_id: release.id,
        question: "未知问题",
        status: "REFUSED",
        direct_answer:
          "当前固定 Release 中没有足够的可见有效证据，无法下结论。",
        key_basis: [],
        uncertainty: "证据不足。",
        citations: [],
        conflicts: [],
      }),
    } as unknown as NexweaveApi;
    render(<AskCenter api={api} spaceId={release.space_id} />);
    await screen.findByText("1.0.0");
    fireEvent.change(screen.getByPlaceholderText("向当前发布提问…"), {
      target: { value: "未知问题" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("证据不足，无法回答")).toBeInTheDocument();
    expect(screen.getByText(/没有足够的可见有效证据/)).toBeInTheDocument();
  });

  it("uses a Release-scoped graph route and renders evidence counts", async () => {
    const graphTraverse = vi.fn().mockResolvedValue({
      release_id: release.id,
      start_entity_id: "018f0000-0000-7000-8000-000000000008",
      mode: "TRAVERSE",
      nodes: [{ id: "018f0000-0000-7000-8000-000000000008" }],
      edges: [
        {
          relation_id: "018f0000-0000-7000-8000-000000000009",
          relation_type_key: "core/related-to",
          source_entity_id: "018f0000-0000-7000-8000-000000000008",
          target_entity_id: "018f0000-0000-7000-8000-000000000010",
          depth: 1,
          evidence_ids: ["018f0000-0000-7000-8000-000000000011"],
        },
      ],
      truncated: true,
    });
    const api = {
      releases: vi.fn().mockResolvedValue({ items: [release] }),
      graphTraverse,
    } as unknown as NexweaveApi;
    render(<GraphCenter api={api} spaceId={release.space_id} />);
    await screen.findByText("1.0.0");
    fireEvent.change(screen.getByPlaceholderText("输入实体标识"), {
      target: { value: "018f0000-0000-7000-8000-000000000008" },
    });
    fireEvent.click(screen.getByRole("button", { name: "遍历三跳" }));
    await waitFor(() =>
      expect(graphTraverse).toHaveBeenCalledWith(
        release.id,
        expect.any(String),
        3,
      ),
    );
    expect(await screen.findByText("core/related-to")).toBeInTheDocument();
    expect(screen.getByText(/证据 1/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("仅展示部分关系");
  });
});
