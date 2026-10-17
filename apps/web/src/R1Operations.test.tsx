import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { StrictMode } from "react";

import { ApiError, type NexweaveApi } from "./api";
import { LoginPage } from "./LoginPage";
import { ClaimCenter, ConflictCenter, ReviewCenter } from "./ReviewCenter";
import { QualityCenter, ReleaseCenter } from "./M7Knowledge";
import { IntegrationCenter } from "./IntegrationCenter";
import { AdminPage } from "./AdminPage";

const dialogMethods = ["showModal", "close"].map(
  (name) =>
    [
      name,
      Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name),
    ] as const,
);

afterEach(() => {
  cleanup();
  for (const [name, descriptor] of dialogMethods) {
    if (descriptor)
      Object.defineProperty(HTMLDialogElement.prototype, name, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  }
  vi.restoreAllMocks();
  vi.useRealTimers();
  history.replaceState({}, "", "/");
});
const schema = {
  id: "schema-b",
  schema_key: "business/b",
  semantic_version: "1.0.0",
  status: "PUBLISHED",
};
const target = {
  id: "candidate-b",
  target_type: "CLAIM_CANDIDATE",
  content: { statement: "Pump B is 70 degrees", created_by: "author" },
  evidence: [
    {
      id: "evidence-b",
      stance: "OPPOSES",
      filename: "contrary.txt",
      anchor_status: "VALID",
      source_version_id: "source-b",
      source_anchor_id: "anchor-b",
      excerpt_hash: "hash",
      locators: [],
    },
  ],
};
const claim = {
  id: "claim-b",
  statement: "Pump B is 70 degrees",
  schema_version_id: "schema-b",
  provenance: {},
  status: "APPROVED",
};

test("new user creation uses the server issuer rather than the unusable local label", async () => {
  // JSDOM lacks native dialog methods; actual dialog behavior is checked in the browser.
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
  const createUser = vi.fn().mockResolvedValue({});
  const api = {
    users: vi.fn().mockResolvedValue({ items: [] }),
    authConfig: vi.fn().mockResolvedValue({
      provider: "local",
      issuer: "https://identity.nexweave.local/dev",
      login_enabled: true,
    }),
    createUser,
  } as unknown as NexweaveApi;
  render(<AdminPage api={api} />);
  fireEvent.click(screen.getByRole("button", { name: /创建用户/ }));
  await waitFor(() =>
    expect(screen.getByLabelText("身份来源")).toHaveValue(
      "https://identity.nexweave.local/dev",
    ),
  );
  fireEvent.change(screen.getByLabelText("账号标识"), {
    target: { value: "technical-engineer" },
  });
  fireEvent.change(screen.getByLabelText("显示名称"), {
    target: { value: "核对工程角色" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建" }));
  await waitFor(() =>
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({
        issuer: "https://identity.nexweave.local/dev",
        subject: "technical-engineer",
        tenant_roles: [],
      }),
    ),
  );
});

test("requires a chosen candidate, policy and substantive reason and exposes opposing source text", async () => {
  const createReviewCase = vi.fn().mockResolvedValue({ id: "case-b" });
  const api = {
    reviewCases: vi.fn().mockResolvedValue({ items: [] }),
    reviewTargets: vi
      .fn()
      .mockResolvedValue({ items: [target], truncated: false }),
    reviewPolicies: vi.fn().mockResolvedValue([
      {
        id: "policy-b",
        risk_level: "HIGH",
        version: 2,
        stages: ["ENGINEERING", "EXPERT", "APPROVAL"],
      },
    ]),
    createReviewCase,
    sourcePreview: vi.fn().mockResolvedValue({
      anchor_status: "VALID",
      locator_results: [{ matched: true, safe_detail: "Line 4" }],
      sanitized_content: "Original text contradicts this value",
    }),
  } as unknown as NexweaveApi;
  render(<ReviewCenter api={api} spaceId="space-b" />);
  const submit = screen.getByRole("button", { name: "绑定当前版本并提交审核" });
  expect(submit).toBeDisabled();
  await screen.findByRole("option", { name: "Pump B is 70 degrees" });
  fireEvent.change(screen.getByLabelText("候选内容"), {
    target: { value: "candidate-b" },
  });
  fireEvent.change(screen.getByLabelText("审核策略"), {
    target: { value: "policy-b" },
  });
  expect(screen.getByText("反对 · contrary.txt")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "核对原文定位" }));
  expect(
    await screen.findByText("Original text contradicts this value"),
  ).toBeInTheDocument();
  expect(submit).toBeDisabled();
  fireEvent.change(screen.getByLabelText("起案理由"), {
    target: {
      value:
        "The supporting and contrary measurements need independent examination",
    },
  });
  fireEvent.click(submit);
  await waitFor(() =>
    expect(createReviewCase).toHaveBeenCalledWith(
      "space-b",
      expect.objectContaining({
        target_id: "candidate-b",
        policy_id: "policy-b",
        risk_level: "HIGH",
        reason:
          "The supporting and contrary measurements need independent examination",
      }),
    ),
  );
});

test("conditional conflict decisions require actual conditions and update the blocking result", async () => {
  const conflict = {
    id: "conflict",
    kind: "CONTRADICTORY_CLAIM",
    status: "OPEN",
    blocking: true,
    items: [
      { ...target, side: "A" },
      {
        ...target,
        id: "other",
        side: "B",
        content: { statement: "Pump B is 90 degrees" },
      },
    ],
    decisions: [],
  };
  const resolveConflict = vi.fn().mockResolvedValue({});
  const conflicts = vi
    .fn()
    .mockResolvedValueOnce({ items: [conflict] })
    .mockResolvedValue({ items: [{ ...conflict, status: "RESOLVED" }] });
  const api = { conflicts, resolveConflict } as unknown as NexweaveApi;
  render(<ConflictCenter api={api} spaceId="space-b" />);
  fireEvent.click(
    await screen.findByRole("button", { name: /CONTRADICTORY_CLAIM/ }),
  );
  expect(screen.getByText("Pump B is 90 degrees")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("裁决方式"), {
    target: { value: "CONDITIONAL" },
  });
  fireEvent.change(screen.getByLabelText("裁决理由"), {
    target: { value: "The measurements use different windows" },
  });
  const button = screen.getByRole("button", { name: "记录裁决并更新阻断" });
  expect(button).toBeDisabled();
  fireEvent.change(screen.getByLabelText("成立条件"), {
    target: { value: "Match the operating window" },
  });
  fireEvent.click(button);
  await waitFor(() =>
    expect(resolveConflict).toHaveBeenCalledWith("conflict", {
      resolution: "CONDITIONAL",
      reason: "The measurements use different windows",
      conditions: { applicability: "Match the operating window" },
    }),
  );
  expect(await screen.findByText("当前不阻断发布")).toBeInTheDocument();
});

test("release uses explicit non-first configuration and exact Claim, Relation and Wiki selections", async () => {
  const createReleaseCandidate = vi.fn().mockResolvedValue({});
  const api = {
    releaseCandidates: vi.fn().mockResolvedValue({ items: [] }),
    releases: vi.fn().mockResolvedValue({ items: [] }),
    evaluationSuites: vi.fn().mockResolvedValue([
      {
        id: "suite-a",
        schema_version_id: "schema-a",
        name: "First suite",
        version: 1,
        cases: [],
      },
      {
        id: "suite-b",
        schema_version_id: "schema-b",
        name: "Chosen suite",
        version: 2,
        cases: [{}],
      },
    ]),
    schemas: vi
      .fn()
      .mockResolvedValue({ items: [{ ...schema, id: "schema-a" }, schema] }),
    claims: vi.fn().mockResolvedValue({
      items: [
        {
          ...claim,
          id: "claim-a",
          statement: "Exclude me",
          schema_version_id: "schema-b",
        },
        claim,
      ],
    }),
    relations: vi.fn().mockResolvedValue({
      items: [
        {
          id: "relation-b",
          schema_version_id: "schema-b",
          relation_type_key: "feeds",
          source_entity_id: "one",
          target_entity_id: "two",
        },
      ],
    }),
    wikiPages: vi.fn().mockResolvedValue({
      items: [
        {
          id: "page-b",
          title: "Chosen Wiki",
          schema_version_id: "schema-b",
          current_version_id: "wiki-version-b",
        },
      ],
    }),
    executionOptions: vi.fn().mockResolvedValue({
      prompt_versions: [
        { id: "prompt-a", prompt_key: "first" },
        { id: "prompt-b", prompt_key: "chosen", revision: 2 },
      ],
      model_profiles: [
        { id: "model-a", name: "first" },
        { id: "model-b", name: "chosen", provider: "external" },
      ],
    }),
    createReleaseCandidate,
  } as unknown as NexweaveApi;
  render(<ReleaseCenter api={api} spaceId="space-b" />);
  expect(
    screen.getByRole("button", { name: "按所选范围创建候选并验证" }),
  ).toBeDisabled();
  await screen.findByRole("option", { name: "chosen · external" });
  fireEvent.change(screen.getByLabelText("发布 Schema"), {
    target: { value: "schema-b" },
  });
  fireEvent.change(screen.getByLabelText("质量套件与版本"), {
    target: { value: "suite-b" },
  });
  fireEvent.change(screen.getByLabelText("Prompt 版本"), {
    target: { value: "prompt-b" },
  });
  fireEvent.change(screen.getByLabelText("模型配置"), {
    target: { value: "model-b" },
  });
  expect(
    screen
      .getAllByRole("checkbox")
      .every((c) => !(c as HTMLInputElement).checked),
  ).toBe(true);
  for (const text of ["Pump B is 70 degrees", /feeds/, /Chosen Wiki/])
    fireEvent.click(screen.getByRole("checkbox", { name: text }));
  fireEvent.change(screen.getByLabelText("SemVer"), {
    target: { value: "2.0.0" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "按所选范围创建候选并验证" }),
  );
  await waitFor(() =>
    expect(createReleaseCandidate).toHaveBeenCalledWith(
      "space-b",
      expect.objectContaining({
        schema_version_id: "schema-b",
        evaluation_suite_id: "suite-b",
        prompt_version_id: "prompt-b",
        model_profile_id: "model-b",
        claim_ids: ["claim-b"],
        relation_ids: ["relation-b"],
        wiki_page_version_ids: ["wiki-version-b"],
      }),
    ),
  );
});

test("quality saves multiple independent expectations and a checked refusal reason", async () => {
  const createEvaluationSuite = vi.fn().mockResolvedValue({});
  const api = {
    evaluationSuites: vi.fn().mockResolvedValue([]),
    schemas: vi.fn().mockResolvedValue({ items: [schema] }),
    claims: vi.fn().mockResolvedValue({ items: [claim] }),
    releaseCandidates: vi.fn().mockResolvedValue({ items: [] }),
    releases: vi.fn().mockResolvedValue({ items: [] }),
    evaluationRuns: vi.fn().mockResolvedValue([]),
    createEvaluationSuite,
  } as unknown as NexweaveApi;
  render(<QualityCenter api={api} spaceId="space-b" />);
  await screen.findByRole("option", { name: "business/b · 1.0.0" });
  fireEvent.change(screen.getByLabelText("知识模型 Schema"), {
    target: { value: "schema-b" },
  });
  fireEvent.change(screen.getByLabelText(/问题集标识/), {
    target: { value: "business/pump-questions" },
  });
  fireEvent.change(screen.getByLabelText("问题集名称"), {
    target: { value: "Independent questions" },
  });
  const first = within(screen.getByRole("group", { name: "问题 1" }));
  fireEvent.change(first.getByLabelText("自然问句"), {
    target: { value: "How hot is Pump B?" },
  });
  fireEvent.change(first.getByLabelText(/预期答案片段/), {
    target: { value: "70\nPump B" },
  });
  fireEvent.click(screen.getByRole("button", { name: "添加问题" }));
  const second = within(screen.getByRole("group", { name: "问题 2" }));
  fireEvent.change(second.getByLabelText("问题类型"), {
    target: { value: "COUNTERFACTUAL" },
  });
  fireEvent.change(second.getByLabelText("自然问句"), {
    target: { value: "Does the unrelated turbine Z999 drive Pump B?" },
  });
  fireEvent.change(second.getByLabelText("拒答条件"), {
    target: { value: "NO_MATCHING_KNOWLEDGE" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "保存问题集新版本（100% 门槛）" }),
  );
  await waitFor(() =>
    expect(createEvaluationSuite).toHaveBeenCalledWith(
      "space-b",
      expect.objectContaining({
        schema_version_id: "schema-b",
        minimum_pass_rate: 100,
        cases: [
          expect.objectContaining({
            expected_terms: ["70", "Pump B"],
            expected_claim_ids: [],
          }),
          expect.objectContaining({
            case_type: "COUNTERFACTUAL",
            expect_refusal: true,
            expected_refusal_reason: "NO_MATCHING_KNOWLEDGE",
          }),
        ],
      }),
    ),
  );
});

test("a space switch clears selected claim detail", async () => {
  const api = {
    claims: vi
      .fn()
      .mockResolvedValueOnce({ items: [claim] })
      .mockResolvedValue({ items: [] }),
  } as unknown as NexweaveApi;
  const view = render(<ClaimCenter api={api} spaceId="old-space" />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Pump B is 70 degrees/ }),
  );
  expect(view.container.querySelector("blockquote")).toHaveTextContent(
    "Pump B is 70 degrees",
  );
  view.rerender(<ClaimCenter api={api} spaceId="new-space" />);
  expect(screen.queryByText("Pump B is 70 degrees")).not.toBeInTheDocument();
});

test("configuration failure does not hide a publisher's pending candidate", async () => {
  const api = {
    executionOptions: vi
      .fn()
      .mockRejectedValue(new Error("selection unavailable")),
    releaseCandidates: vi.fn().mockResolvedValue({
      items: [
        {
          id: "pending",
          version: "1.0.1",
          status: "PENDING_APPROVAL",
          gate_summary: {
            evaluation_passed: true,
            traceability_percent: 100,
          },
          lint_findings: [],
          evaluation_suite_id: "suite",
        },
      ],
    }),
    releases: vi.fn().mockResolvedValue({ items: [] }),
    evaluationSuites: vi.fn().mockResolvedValue([]),
    schemas: vi.fn().mockResolvedValue({ items: [] }),
    claims: vi.fn().mockResolvedValue({ items: [] }),
    relations: vi.fn().mockResolvedValue({ items: [] }),
    wikiPages: vi.fn().mockResolvedValue({ items: [] }),
  } as unknown as NexweaveApi;
  render(<ReleaseCenter api={api} spaceId="publisher-space" />);
  expect(await screen.findByText("1.0.1")).toBeInTheDocument();
  expect(screen.getByText(/创建配置暂不可用/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("独立批准的实质理由"), {
    target: { value: "Checked the fixed candidate and actual evaluation" },
  });
  expect(
    screen.getByRole("button", { name: "批准此候选并发布" }),
  ).toBeEnabled();
});

test("connector save does not claim a connection test and sync polls to a real terminal response", async () => {
  vi.useFakeTimers();
  const api = {
    connectorInstances: vi.fn().mockResolvedValue({
      items: [
        {
          id: "connector",
          name: "Synthetic readonly",
          kind: "S3",
          status: "ACTIVE",
          watermark: {},
        },
      ],
    }),
    listGovernance: vi.fn().mockResolvedValue({ items: [] }),
    startConnectorSync: vi.fn().mockResolvedValue({
      id: "sync",
      status: "RUNNING",
      workflow_id: "workflow",
    }),
    connectorSyncRun: vi.fn().mockResolvedValue({
      id: "sync",
      status: "SUCCEEDED",
      workflow_id: "workflow",
    }),
  } as unknown as NexweaveApi;
  render(<IntegrationCenter api={api} spaceId="space-b" />);
  await act(async () => {});
  fireEvent.click(screen.getByRole("button", { name: "+ 创建集成" }));
  expect(
    screen.getByRole("button", { name: "保存配置（不测试连接）" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "开始同步" }));
  await act(async () => {});
  await act(async () => vi.advanceTimersByTimeAsync(2100));
  expect(api.connectorSyncRun).toHaveBeenCalledWith("sync");
  expect(screen.getByText("已成功")).toBeInTheDocument();
});

test("OIDC mode shows no development form and consumes callback once under StrictMode", async () => {
  const onSession = vi.fn();
  history.replaceState({}, "", "/auth/callback?code=one-code&state=one-state");
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input) =>
      new Response(
        JSON.stringify(
          String(input).endsWith("/auth/config")
            ? {
                provider: "oidc",
                login_enabled: true,
                login_url: "/api/v1/auth/oidc/login",
                logout_url: null,
              }
            : { access_token: "verified-token", expires_in: 600 },
        ),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
  );
  render(
    <StrictMode>
      <LoginPage initialError="" onSession={onSession} />
    </StrictMode>,
  );
  await waitFor(() =>
    expect(onSession).toHaveBeenCalledWith("verified-token", 600),
  );
  expect(location.search).toBe("");
  expect(
    vi
      .mocked(fetch)
      .mock.calls.filter(([url]) =>
        String(url).endsWith("/auth/oidc/exchange"),
      ),
  ).toHaveLength(1);
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "验证身份并进入" }),
  ).not.toBeInTheDocument();
});

test("explains authoritative review separation instead of suggesting a refresh", () => {
  const denied = new ApiError(
    "High-risk final approval must be independent.",
    409,
    "REVIEW_DUTY_SEPARATION",
  );
  expect(denied.message).toContain("内容原作者");
  expect(denied.message).toContain("不能终审");
});
