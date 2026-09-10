"""M9.5 provider-neutral operational and forecast contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import UUID7, AwareDatetime, Field, FiniteFloat, model_validator

from nexweave_contracts.base import ContractModel
from nexweave_contracts.release import CitationResponse


class ForecastKnowledgeRequest(ContractModel):
    release_id: UUID7
    question: str = Field(min_length=1, max_length=1000, pattern=r"\S")


class ForecastKnowledgeItem(ContractModel):
    claim_id: UUID7
    source_document_id: UUID7
    statement: str
    citation: CitationResponse


class ForecastKnowledgeContext(ContractModel):
    artifact_id: UUID7
    artifact_checksum: str
    release_id: UUID7
    release_checksum: str
    release_deprecated: bool
    query_answer_id: UUID7
    question: str
    checked_at: AwareDatetime
    status: Literal["CITED_CONTEXT", "INSUFFICIENT_EVIDENCE"]
    epistemic_kind: Literal["RELEASED_KNOWLEDGE_CONTEXT"] = "RELEASED_KNOWLEDGE_CONTEXT"
    items: tuple[ForecastKnowledgeItem, ...]
    explanation: str
    limitations: tuple[str, ...]


KEY = r"^[a-z][a-z0-9.-]{1,62}/[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"


class SignalDefinition(ContractModel):
    key: str = Field(pattern=KEY)
    typeKey: str = Field(pattern=KEY)
    displayName: str = Field(min_length=1, max_length=128)
    unit: str = Field(min_length=1, max_length=32)
    quantity: str = Field(min_length=1, max_length=128)


class ForecastProfile(ContractModel):
    key: str = Field(pattern=KEY)
    displayName: str = Field(min_length=1, max_length=128)
    target: str = Field(pattern=KEY)
    pastCovariates: tuple[str, ...] = Field(default=(), max_length=8)
    futureCovariates: tuple[str, ...] = Field(default=(), max_length=8)
    frequencySeconds: int = Field(default=60, ge=1, le=86400)
    maxHorizon: int = Field(default=120, ge=1, le=120)

    @model_validator(mode="after")
    def distinct_roles(self) -> "ForecastProfile":
        keys = (self.target, *self.pastCovariates, *self.futureCovariates)
        if len(set(keys)) != len(keys):
            raise ValueError("Each signal must have exactly one role in this profile.")
        return self


class SignalColumn(ContractModel):
    signal_key: str = Field(pattern=KEY)
    column: str = Field(min_length=1, max_length=128)
    unit: str = Field(min_length=1, max_length=32)


class BindingCreate(ContractModel):
    name: str = Field(min_length=1, max_length=255)
    entity_id: UUID7
    schema_version_id: UUID7
    source_version_id: UUID7
    profile_key: str = Field(pattern=KEY)
    timestamp_column: str = Field(default="timestamp", min_length=1, max_length=128)
    columns: tuple[SignalColumn, ...] = Field(min_length=1, max_length=9)
    quality_column: str | None = Field(default=None, min_length=1, max_length=128)
    data_kind: Literal["SYNTHETIC", "IMPORTED_UNVERIFIED"]
    operating_context: str = Field(default="工况尚未核实", max_length=1000)


class BindingResponse(BindingCreate):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    classification: str
    status: Literal["ACTIVE"] = "ACTIVE"
    version: int = 1
    snapshot: dict[str, Any]
    created_at: datetime


class BindingList(ContractModel):
    items: tuple[BindingResponse, ...]


class FuturePath(ContractModel):
    signal_key: str = Field(pattern=KEY)
    unit: str = Field(min_length=1, max_length=32)
    values: tuple[FiniteFloat, ...] = Field(min_length=1, max_length=120)


class EventRule(ContractModel):
    threshold: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=32)
    label: str = Field(default="上分位进入关注区间", min_length=1, max_length=128)
    authority: Literal["DEMONSTRATION_ONLY", "USER_DEFINED_UNVERIFIED"]


class ForecastCreate(ContractModel):
    binding_id: UUID7
    provider_id: Literal["chronos2", "persistence"] = "chronos2"
    horizon: int = Field(default=120, ge=1, le=120)
    history_points: int = Field(default=720, ge=32, le=8192)
    cutoff: AwareDatetime | None = None
    scenario_name: str = Field(default="基线假设", min_length=1, max_length=128)
    future_paths: tuple[FuturePath, ...] = Field(default=(), max_length=8)
    event_rule: EventRule | None = None
    release_id: UUID7 | None = None


class ForecastRunResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    binding_id: UUID7
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
    workflow_id: str
    delivery_status: str = "PENDING"
    delivery_attempts: int = 0
    delivery_error_code: str | None = None
    retry_of: UUID7 | None = None
    artifact_id: UUID7 | None = None
    error_code: str | None = None
    request: ForecastCreate
    created_at: datetime
    updated_at: datetime


class ForecastRunList(ContractModel):
    items: tuple[ForecastRunResponse, ...]


class ForecastArtifactResponse(ContractModel):
    id: UUID7
    run_id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    classification: str
    epistemic_kind: Literal["FORECAST"] = "FORECAST"
    data_kind: Literal["SYNTHETIC", "IMPORTED_UNVERIFIED"]
    content_checksum: str
    content: dict[str, Any]
    created_at: datetime


class ForecastEventData(ContractModel):
    """Payload of the existing EventEnvelope; event type identifies the transition."""

    id: UUID7
    binding_id: UUID7 | None = None
    source_version_id: UUID7 | None = None
    provider_id: str | None = None
    artifact_id: UUID7 | None = None
    content_checksum: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    error_code: str | None = None


class TimeSeriesCapabilities(ContractModel):
    provider_id: str
    model_revision: str
    past_covariates: bool
    known_future_covariates: bool
    quantiles: tuple[float, ...]
    max_history: int = 8192
    max_horizon: int = 120
    execution: Literal["LOCAL_CPU"] = "LOCAL_CPU"


class ForecastCommand(ContractModel):
    reason: str = Field(min_length=1, max_length=1000)


class ForecastRuntime(ContractModel):
    worker_status: Literal["AVAILABLE", "UNAVAILABLE"]
    worker_count: int
    queued: int
    running: int
    delivery_pending: int
    implementation_version: str


class CsvBindingPreview(ContractModel):
    source_version_id: UUID7
    checksum: str
    columns: tuple[str, ...] = Field(max_length=32)
    sample_rows: tuple[dict[str, str], ...] = Field(max_length=5)
    row_count: int = Field(ge=32, le=20000)


class BindingValidation(ContractModel):
    valid: Literal[True] = True
    point_count: int
    start: AwareDatetime
    end: AwareDatetime
    latest_values: dict[str, FiniteFloat]
    source_checksum: str


class BindingEntity(ContractModel):
    id: UUID7
    schema_version_id: UUID7
    type_key: str
    display_name: str


class BindingEntities(ContractModel):
    items: tuple[BindingEntity, ...]
