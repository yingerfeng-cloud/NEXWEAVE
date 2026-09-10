import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { NexweaveApi } from "./api";
import { PackCenter } from "./PackCenter";
import { SchemaStudio } from "./SchemaStudio";
import type { DomainPackInstallation, SchemaVersion } from "./types";

const schema: SchemaVersion = {
  id: "schema-version-1",
  tenant_id: "tenant-1",
  space_id: "space-1",
  schema_definition_id: "schema-1",
  schema_key: "example.org/equipment",
  semantic_version: "0.2.0",
  status: "DRAFT",
  content_checksum: `sha256:${"a".repeat(64)}`,
  composition_checksum: `sha256:${"b".repeat(64)}`,
  canonicalization_algorithm: "RFC8785-JCS/1",
  breaking_change: false,
  normalized_snapshot: { types: [{ key: "example.org/equipment" }] },
  version: 1,
  created_at: "2026-08-30T00:00:00Z",
  created_by: "actor-1",
  updated_at: "2026-08-30T00:00:00Z",
  updated_by: "actor-1",
};

const installation: DomainPackInstallation = {
  id: "installation-1",
  tenant_id: "tenant-1",
  space_id: "space-1",
  domain_pack_version_id: "pack-version-1",
  schema_definition_id: "schema-1",
  requested_semantic_version: "0.2.0",
  operation: "INSTALL",
  previous_installation_id: null,
  workflow_task_id: "task-1",
  workflow_id: "workflow-1",
  run_id: "run-1",
  candidate_schema_version_id: "schema-version-1",
  composition_report_id: "report-1",
  status: "ACTIVE",
  version: 2,
  created_at: "2026-08-30T00:00:00Z",
  created_by: "actor-1",
  updated_at: "2026-08-30T00:00:01Z",
  updated_by: "actor-1",
};

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});

test("Schema Studio keeps validation and publication as separate actions", async () => {
  const validateSchema = vi.fn().mockResolvedValue({
    id: "report-1",
    schema_version_id: schema.id,
    input_checksum: schema.composition_checksum,
    result_checksum: schema.content_checksum,
    report: { compatible: true },
  });
  const api = {
    schemas: vi.fn().mockResolvedValue({ items: [schema] }),
    createSchema: vi.fn(),
    validateSchema,
    publishSchema: vi.fn(),
  } as unknown as NexweaveApi;

  render(<SchemaStudio api={api} spaceId="space-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "验证" }));

  await waitFor(() => expect(validateSchema).toHaveBeenCalledWith(schema));
  expect(screen.getByRole("heading", { name: "组合报告" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "发布" })).toBeDisabled();
});

test("Pack Center installs a trusted version and exposes its candidate without publishing", async () => {
  const installDomainPack = vi.fn().mockResolvedValue(installation);
  const api = {
    domainPacks: vi.fn().mockResolvedValue({
      items: [
        {
          id: "pack-version-1",
          tenant_id: "tenant-1",
          pack_key: "equipment-pack",
          pack_version: "1.0.0",
          publisher: "Example",
          key_namespace: "example.org",
          content_checksum: `sha256:${"c".repeat(64)}`,
          signature_key_id: "fixture-key",
          status: "PUBLISHED",
          created_at: "2026-08-30T00:00:00Z",
        },
      ],
    }),
    schemas: vi.fn().mockResolvedValue({ items: [schema] }),
    installDomainPack,
    domainPackInstallation: vi.fn(),
    disableDomainPack: vi.fn(),
    rollbackDomainPack: vi.fn(),
  } as unknown as NexweaveApi;

  render(<PackCenter api={api} spaceId="space-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "安装" }));

  await waitFor(() =>
    expect(installDomainPack).toHaveBeenCalledWith("space-1", {
      domain_pack_version_id: "pack-version-1",
      schema_definition_id: "schema-1",
      semantic_version: "0.2.0",
    }),
  );
  expect(
    screen.getByRole("heading", { name: "最近安装" }).parentElement,
  ).toHaveTextContent("安装状态已由可靠任务记录");
  expect(screen.getByText(/schema-version-1/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "发布" })).toBeNull();
});
