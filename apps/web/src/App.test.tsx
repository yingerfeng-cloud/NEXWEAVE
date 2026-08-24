import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows the real M0 boundary and infrastructure readiness", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          product: "NEXWEAVE",
          release: "R1",
          milestone: "M0",
          build_version: "0.1.0-test",
        }),
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "ready",
          components: {
            postgresql: { status: "up" },
            object_storage: { status: "up" },
            temporal: { status: "up" },
          },
        }),
      ),
    );

  render(<App />);

  await waitFor(() =>
    expect(screen.getByText("工程骨架就绪")).toBeInTheDocument(),
  );
  expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
  expect(screen.getByText("RustFS / S3")).toBeInTheDocument();
  expect(
    screen.getByText(/未包含：资料、Schema、编译、审核、发布、问答/),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: /资料中心/ }),
  ).not.toBeInTheDocument();
});
