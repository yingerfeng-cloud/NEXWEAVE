import { expect, test } from "vitest";
import { compatibleForecasts } from "./livingComparison";
import type { ForecastArtifact } from "./livingTypes";

const artifact: ForecastArtifact = {
  id: "one",
  content_checksum: "hash",
  data_kind: "SYNTHETIC",
  content: {
    binding_id: "binding",
    context: {
      source_version_id: "source",
      schema_version_id: "schema",
      entity_id: "entity",
      origin: "2026-09-01T00:00:00Z",
      unit: "degC",
      target: "test/temp",
      observations: [
        { timestamp: "2026-09-01T00:00:00Z", values: { "test/temp": 40 } },
      ],
      prediction_timestamps: ["2026-09-01T00:01:00Z"],
      scenario_name: "baseline",
      operating_context: "synthetic",
    },
    result: {
      provider_id: "chronos2",
      model_revision: "pinned",
      quantiles: { "0.5": [41] },
    },
    potential_events: [],
    event_evaluation: "NOT_EVALUATED",
    hypotheses: [],
    risk_narrative: {
      observed: "",
      forecast: "",
      knowledge: "",
      limitations: [],
    },
    released_knowledge: { status: "NO_RELEASE_SELECTED" },
  },
};

test("same history can compare conditions without treating revisions or windows as equivalent", () => {
  const b = structuredClone(artifact);
  b.id = "two";
  b.content.context.scenario_name = "different condition";
  expect(compatibleForecasts(artifact, b)).toBe(true);
  b.content.context.observations[0].values["test/temp"] = 41;
  expect(compatibleForecasts(artifact, b)).toBe(false);
  b.content.context.observations[0].values["test/temp"] = 40;
  b.content.result.model_revision = "another revision";
  expect(compatibleForecasts(artifact, b)).toBe(false);
  b.content.result.model_revision = "pinned";
  b.content.binding_id = "another binding";
  expect(compatibleForecasts(artifact, b)).toBe(false);
});
