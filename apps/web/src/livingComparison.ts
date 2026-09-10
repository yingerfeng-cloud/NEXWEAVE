import type { ForecastArtifact } from "./livingTypes";

export function compatibleForecasts(
  a: ForecastArtifact,
  b: ForecastArtifact,
): boolean {
  const ac = a.content.context,
    bc = b.content.context;
  return (
    a.id !== b.id &&
    a.content.binding_id === b.content.binding_id &&
    JSON.stringify(ac.observations) === JSON.stringify(bc.observations) &&
    ac.target === bc.target &&
    ac.unit === bc.unit &&
    ac.source_version_id === bc.source_version_id &&
    ac.schema_version_id === bc.schema_version_id &&
    ac.entity_id === bc.entity_id &&
    JSON.stringify(ac.prediction_timestamps) ===
      JSON.stringify(bc.prediction_timestamps) &&
    a.content.result.provider_id === b.content.result.provider_id &&
    a.content.result.model_revision === b.content.result.model_revision
  );
}
