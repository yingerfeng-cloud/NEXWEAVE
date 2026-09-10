export type Signal = {
  key: string;
  displayName: string;
  unit: string;
  quantity: string;
};
export type SignalBinding = {
  id: string;
  name: string;
  entity_id: string;
  schema_version_id: string;
  source_version_id: string;
  data_kind: string;
  operating_context: string;
  snapshot: {
    signals: Signal[];
    entity: { display_name: string };
    profile: {
      target: string;
      pastCovariates: string[];
      futureCovariates: string[];
      frequencySeconds: number;
      maxHorizon: number;
    };
  };
};
export type ForecastRequest = {
  binding_id: string;
  provider_id: "chronos2" | "persistence";
  horizon: number;
  history_points: number;
  scenario_name: string;
  future_paths: { signal_key: string; unit: string; values: number[] }[];
  event_rule?: {
    threshold: number;
    unit: string;
    label: string;
    authority: "USER_DEFINED_UNVERIFIED";
  };
};
export type ForecastRun = {
  id: string;
  status: string;
  delivery_status: "PENDING" | "ACCEPTED" | "RETRYING" | "TERMINAL";
  delivery_attempts: number;
  delivery_error_code: string | null;
  retry_of: string | null;
  artifact_id: string | null;
  error_code: string | null;
  request: ForecastRequest;
  created_at: string;
};
export type ForecastArtifact = {
  id: string;
  content_checksum: string;
  data_kind: string;
  content: {
    binding_id: string;
    context: {
      source_version_id: string;
      schema_version_id: string;
      entity_id: string;
      origin: string;
      unit: string;
      target: string;
      observations: { timestamp: string; values: Record<string, number> }[];
      prediction_timestamps: string[];
      scenario_name: string;
      operating_context: string;
    };
    result: {
      provider_id: string;
      model_revision: string;
      quantiles: Record<string, number[]>;
    };
    potential_events: {
      label: string;
      first_timestamp: string;
      explanation: string;
    }[];
    event_evaluation: string;
    hypotheses: { statement: string; verification: string }[];
    risk_narrative: {
      observed: string;
      forecast: string;
      knowledge: string;
      limitations: string[];
    };
    released_knowledge: { status: string };
  };
};

export type ForecastRuntime = {
  worker_status: "AVAILABLE" | "UNAVAILABLE";
  worker_count: number;
  queued: number;
  running: number;
  delivery_pending: number;
  implementation_version: string;
};

export type ForecastKnowledgeContext = {
  artifact_id: string;
  artifact_checksum: string;
  release_id: string;
  release_checksum: string;
  release_deprecated: boolean;
  query_answer_id: string;
  question: string;
  checked_at: string;
  status: "CITED_CONTEXT" | "INSUFFICIENT_EVIDENCE";
  explanation: string;
  limitations: string[];
  items: {
    claim_id: string;
    statement: string;
    source_document_id: string;
    citation: {
      id: string;
      release_id: string;
      evidence_id: string;
      source_version_id: string;
      source_anchor_id: string;
      locator: Record<string, unknown>;
    };
  }[];
};
export const forecastStatusLabel: Record<string, string> = {
  QUEUED: "等待运行",
  RUNNING: "正在预测",
  SUCCEEDED: "已完成",
  FAILED: "运行失败",
  CANCELLED: "已取消",
};

export const forecastProviderLabel: Record<string, string> = {
  chronos2: "Chronos-2",
  persistence: "持久化基线",
};

export type BindingInput = {
  name: string;
  entity_id: string;
  schema_version_id: string;
  source_version_id: string;
  profile_key: string;
  timestamp_column: string;
  columns: { signal_key: string; column: string; unit: string }[];
  quality_column: string | null;
  data_kind: "SYNTHETIC" | "IMPORTED_UNVERIFIED";
  operating_context: string;
};
export type BindingValidation = {
  valid: true;
  point_count: number;
  start: string;
  end: string;
  latest_values: Record<string, number>;
  source_checksum: string;
};
export type CsvBindingPreview = {
  source_version_id: string;
  checksum: string;
  columns: string[];
  sample_rows: Record<string, string>[];
  row_count: number;
};
export type BindingEntity = {
  id: string;
  display_name: string;
  type_key: string;
  schema_version_id: string;
};
export type TemporalSchema = {
  signalDefinitions: (Signal & { typeKey: string })[];
  forecastProfiles: {
    key: string;
    displayName: string;
    target: string;
    pastCovariates: string[];
    futureCovariates: string[];
    frequencySeconds: number;
    maxHorizon: number;
  }[];
};
