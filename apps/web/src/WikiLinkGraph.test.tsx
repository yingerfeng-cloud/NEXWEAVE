import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { NexweaveApi } from "./api";
import { WikiLinkGraphCenter } from "./WikiLinkGraph";

const spaceId = "01989e3f-0b29-7000-8000-000000000001";
const alphaId = "01989e3f-0b29-7000-8000-000000000002";
const betaId = "01989e3f-0b29-7000-8000-000000000003";

afterEach(cleanup);

describe("WikiLinkGraphCenter", () => {
  it("renders bidirectional Wiki navigation and opens a selected page", async () => {
    const wikiLinkGraph = vi.fn().mockResolvedValue({
      space_id: spaceId,
      focus_page_id: null,
      max_depth: 2,
      node_limit: 180,
      truncated: false,
      nodes: [
        {
          id: alphaId,
          title: "编译规范",
          template_key: "core/note",
          status: "DRAFT",
          version: 2,
          updated_at: "2026-08-31T00:00:00Z",
          outbound_count: 1,
          backlink_count: 0,
        },
        {
          id: betaId,
          title: "发布规则",
          template_key: "core/policy",
          status: "DRAFT",
          version: 1,
          updated_at: "2026-08-31T00:00:00Z",
          outbound_count: 0,
          backlink_count: 1,
        },
      ],
      edges: [
        {
          id: "01989e3f-0b29-7000-8000-000000000004",
          source_page_id: alphaId,
          target_page_id: betaId,
          link_kind: "WIKI_LINK",
        },
      ],
    });
    const onOpenWikiPage = vi.fn();
    render(
      <WikiLinkGraphCenter
        api={{ wikiLinkGraph } as unknown as NexweaveApi}
        spaceId={spaceId}
        onOpenWikiPage={onOpenWikiPage}
        onShowReleaseGraph={vi.fn()}
      />,
    );

    expect(await screen.findByText("编译规范")).toBeInTheDocument();
    expect(screen.getByText("发布规则")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "聚焦页面 编译规范" }));
    await waitFor(() =>
      expect(wikiLinkGraph).toHaveBeenLastCalledWith(spaceId, alphaId),
    );
    fireEvent.click(screen.getByRole("button", { name: "打开 Wiki 页面" }));
    expect(onOpenWikiPage).toHaveBeenCalledWith(alphaId);
  });

  it("filters nodes by title or template key", async () => {
    const api = {
      wikiLinkGraph: vi.fn().mockResolvedValue({
        space_id: spaceId,
        focus_page_id: null,
        max_depth: 2,
        node_limit: 180,
        truncated: false,
        nodes: [
          {
            id: alphaId,
            title: "编译规范",
            template_key: "core/note",
            status: "DRAFT",
            version: 1,
            updated_at: "2026-08-31T00:00:00Z",
            outbound_count: 0,
            backlink_count: 0,
          },
          {
            id: betaId,
            title: "发布规则",
            template_key: "core/policy",
            status: "DRAFT",
            version: 1,
            updated_at: "2026-08-31T00:00:00Z",
            outbound_count: 0,
            backlink_count: 0,
          },
        ],
        edges: [],
      }),
    } as unknown as NexweaveApi;
    render(
      <WikiLinkGraphCenter
        api={api}
        spaceId={spaceId}
        onOpenWikiPage={vi.fn()}
        onShowReleaseGraph={vi.fn()}
      />,
    );

    await screen.findByText("编译规范");
    fireEvent.change(screen.getByPlaceholderText("按页面标题或模板筛选"), {
      target: { value: "policy" },
    });
    expect(screen.queryByText("编译规范")).not.toBeInTheDocument();
    expect(screen.getByText("发布规则")).toBeInTheDocument();
  });

  it("filters the canvas by page template and can hide labels", async () => {
    const api = {
      wikiLinkGraph: vi.fn().mockResolvedValue({
        space_id: spaceId,
        focus_page_id: null,
        max_depth: 2,
        node_limit: 180,
        truncated: false,
        nodes: [
          {
            id: alphaId,
            title: "编译规范",
            template_key: "core/note",
            status: "DRAFT",
            version: 1,
            updated_at: "2026-08-31T00:00:00Z",
            outbound_count: 0,
            backlink_count: 0,
          },
          {
            id: betaId,
            title: "发布规则",
            template_key: "core/policy",
            status: "DRAFT",
            version: 1,
            updated_at: "2026-08-31T00:00:00Z",
            outbound_count: 0,
            backlink_count: 0,
          },
        ],
        edges: [],
      }),
    } as unknown as NexweaveApi;
    render(
      <WikiLinkGraphCenter
        api={api}
        spaceId={spaceId}
        onOpenWikiPage={vi.fn()}
        onShowReleaseGraph={vi.fn()}
      />,
    );

    await screen.findByText("编译规范");
    fireEvent.click(screen.getByRole("button", { name: "core/policy" }));
    expect(screen.queryByText("编译规范")).not.toBeInTheDocument();
    expect(screen.getByText("发布规则")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "隐藏标签" }));
    expect(screen.queryByText("发布规则")).not.toBeInTheDocument();
  });
});
