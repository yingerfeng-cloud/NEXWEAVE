import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import type { NexweaveApi } from "./api";
import { SpacesPage } from "./SpacesPage";
import type { Organization, Principal, Space } from "./types";

afterEach(cleanup);

const principal: Principal = {
  actor_type: "USER",
  actor_id: "actor-1",
  tenant_id: "tenant-1",
  subject: "tenant-admin",
  roles: ["tenant_admin"],
  clearance: "HIGHLY_RESTRICTED",
};

const organization: Organization = {
  id: "organization-1",
  tenant_id: principal.tenant_id,
  slug: "operations",
  display_name: "运营组织",
  status: "ACTIVE",
  version: 1,
};

const createdSpace: Space = {
  id: "space-1",
  tenant_id: principal.tenant_id,
  organization_id: organization.id,
  slug: "quality-platform",
  display_name: "质量平台",
  description: "R1 walkthrough",
  default_classification: "INTERNAL",
  status: "ACTIVE",
  version: 1,
  created_at: "2026-09-13T00:00:00Z",
  updated_at: "2026-09-13T00:00:00Z",
};

test("keeps a successful space creation out of the network-error path", async () => {
  const api = {
    organizations: vi.fn().mockResolvedValue({ items: [organization] }),
    users: vi.fn().mockResolvedValue({ items: [] }),
    createSpace: vi.fn().mockResolvedValue(createdSpace),
  } as unknown as NexweaveApi;
  const onChanged = vi.fn().mockResolvedValue(undefined);
  const onSelect = vi.fn();

  render(
    <SpacesPage
      api={api}
      principal={principal}
      spaces={[]}
      onSelect={onSelect}
      onChanged={onChanged}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "+ 创建知识空间" }));
  await screen.findByRole("option", { name: "运营组织" });
  fireEvent.change(screen.getByLabelText("标识"), {
    target: { value: "quality-platform" },
  });
  fireEvent.change(screen.getByLabelText("名称"), {
    target: { value: "质量平台" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建" }));

  await waitFor(() => expect(onSelect).toHaveBeenCalledWith(createdSpace.id));
  expect(onChanged).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("已创建");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("reports a refresh issue separately after the create request succeeds", async () => {
  const api = {
    organizations: vi.fn().mockResolvedValue({ items: [organization] }),
    users: vi.fn().mockResolvedValue({ items: [] }),
    createSpace: vi.fn().mockResolvedValue(createdSpace),
  } as unknown as NexweaveApi;
  const onChanged = vi.fn().mockRejectedValue(new TypeError("offline"));
  const onSelect = vi.fn();

  render(
    <SpacesPage
      api={api}
      principal={principal}
      spaces={[]}
      onSelect={onSelect}
      onChanged={onChanged}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "+ 创建知识空间" }));
  await screen.findByRole("option", { name: "运营组织" });
  fireEvent.change(screen.getByLabelText("标识"), {
    target: { value: "quality-platform" },
  });
  fireEvent.change(screen.getByLabelText("名称"), {
    target: { value: "质量平台" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建" }));

  await waitFor(() => expect(onSelect).toHaveBeenCalledWith(createdSpace.id));
  expect(screen.getByRole("status")).toHaveTextContent("已创建");
  expect(screen.getByRole("alert")).toHaveTextContent("目录刷新暂时失败");
  expect(
    screen.getByRole("button", { name: "重试目录刷新" }),
  ).toBeInTheDocument();
});
