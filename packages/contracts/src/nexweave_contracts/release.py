"""M7 quality, immutable Release, graph and trusted-query contracts."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel


class EvaluationCaseInput(ContractModel):
    case_key: str = Field(pattern=r"^[a-z][a-z0-9._-]{1,126}$")
    case_type: Literal[
        "ANSWERABLE",
        "UNANSWERABLE",
        "COUNTERFACTUAL",
        "CONFLICT",
        "MULTI_SOURCE",
        "INSUFFICIENT_EVIDENCE",
    ]
    question: str = Field(min_length=1, max_length=4000)
    expected_claim_ids: tuple[UUID7, ...] = ()
    expected_terms: tuple[str, ...] = ()
    expect_refusal: bool = False
    expected_refusal_reason: Literal["NO_MATCHING_KNOWLEDGE", "EVIDENCE_UNAVAILABLE"] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def meaningful_expectations(self) -> "EvaluationCaseInput":
        refusal = self.expect_refusal or self.case_type in {
            "UNANSWERABLE",
            "INSUFFICIENT_EVIDENCE",
            "COUNTERFACTUAL",
        }
        if not self.question.strip() or any(not term.strip() for term in self.expected_terms):
            raise ValueError("questions and expected terms must be nonblank")
        if not refusal and not (self.expected_claim_ids or self.expected_terms):
            raise ValueError("answerable cases require expected claims or answer terms")
        if self.expected_refusal_reason is not None and not refusal:
            raise ValueError("refusal reasons apply only to refusal cases")
        return self


class EvaluationSuiteCreate(ContractModel):
    schema_version_id: UUID7
    suite_key: str = Field(pattern=r"^[a-z][a-z0-9.-]{1,62}/[a-z][a-z0-9-]{0,62}$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    cases: tuple[EvaluationCaseInput, ...] = Field(min_length=1, max_length=500)
    minimum_pass_rate: int = Field(default=100, ge=0, le=100)

    @model_validator(mode="after")
    def unique_case_keys(self) -> "EvaluationSuiteCreate":
        if len({case.case_key for case in self.cases}) != len(self.cases):
            raise ValueError("evaluation case keys must be unique")
        return self


class EvaluationSuiteResponse(EvaluationSuiteCreate):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    status: str
    created_at: datetime
    created_by: UUID7


class EvaluationRunCreate(ContractModel):
    suite_id: UUID7
    target_type: Literal["RELEASE_CANDIDATE", "RELEASE"]
    target_id: UUID7
    retrieval_strategy: Literal["KEYWORD", "ATTRIBUTE", "SEMANTIC", "HYBRID"] = "KEYWORD"
    retrieval_config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def supported_retrieval_config(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        config = value.get("retrieval_config", {})
        if not isinstance(config, dict) or set(config) - {"top_k", "filters"}:
            raise ValueError("evaluation retrieval config supports top_k and filters only")
        # Validate the same strategy/filter contract, without executing a question.
        checked = QueryCreate(
            question="configuration validation",
            client_request_id="configuration",
            strategy=value.get("retrieval_strategy", "HYBRID"),
            **config,
        )
        return {**value, "retrieval_config": {"top_k": checked.top_k, "filters": checked.filters}}


class EvaluationCaseResult(ContractModel):
    case_key: str
    case_type: str
    passed: bool
    answer_status: str
    matched_claim_ids: tuple[UUID7, ...] = ()
    error_code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunResponse(ContractModel):
    result_visibility: Literal["FULL", "METADATA_ONLY"] = "FULL"
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    suite_id: UUID7
    suite_version: int
    target_type: str
    target_id: UUID7
    workflow_task_id: UUID7 | None = None
    workflow_id: str | None = None
    retrieval_strategy: str
    retrieval_config: dict[str, Any]
    status: str
    metrics: dict[str, Any]
    gate_passed: bool | None = None
    error_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    created_by: UUID7
    results: tuple[EvaluationCaseResult, ...] = ()


class ReleaseCandidateCreate(ContractModel):
    version: str = Field(min_length=5, max_length=64)
    schema_version_id: UUID7
    prompt_version_id: UUID7
    model_profile_id: UUID7
    evaluation_suite_id: UUID7
    claim_ids: tuple[UUID7, ...] = ()
    relation_ids: tuple[UUID7, ...] = ()
    wiki_page_version_ids: tuple[UUID7, ...] = ()
    index_config: dict[str, Any] = Field(
        default_factory=lambda: {"version": "r1-query-v3", "retrieval_strategy": "KEYWORD"}
    )
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def valid_index(self) -> "ReleaseCandidateCreate":
        allowed = {
            "version",
            "fusion",
            "vector_dimensions",
            "retrieval_strategy",
            "embedding_model_profile_id",
            "query_config",
        }
        if set(self.index_config) - allowed:
            raise ValueError("unknown release index configuration")
        strategy = self.index_config.get("retrieval_strategy", "KEYWORD")
        if strategy not in {"KEYWORD", "ATTRIBUTE", "SEMANTIC", "HYBRID"}:
            raise ValueError("unsupported retrieval strategy")
        if strategy in {"SEMANTIC", "HYBRID"} and not self.index_config.get(
            "embedding_model_profile_id"
        ):
            raise ValueError("a real embedding profile is required")
        config = self.index_config.get("query_config", {})
        if not isinstance(config, dict) or set(config) - {"top_k", "filters"}:
            raise ValueError("unsupported query configuration")
        QueryCreate.model_validate(
            {
                "client_request_id": "validate-index-config",
                "question": "Validate retrieval configuration",
                "strategy": strategy,
                **config,
            }
        )
        if self.index_config.get("embedding_model_profile_id"):
            from uuid import UUID

            UUID(str(self.index_config["embedding_model_profile_id"]))
        return self

    @model_validator(mode="after")
    def has_knowledge(self) -> "ReleaseCandidateCreate":
        if not (self.claim_ids or self.relation_ids or self.wiki_page_version_ids):
            raise ValueError("ReleaseCandidate requires at least one explicit knowledge object")
        return self


class LintFindingResponse(ContractModel):
    id: UUID7
    code: str
    severity: str
    blocking: bool
    object_type: str
    object_id: UUID7 | None = None
    message: str
    details: dict[str, Any]


class ReleaseCandidateResponse(ContractModel):
    manifest_visibility: Literal["FULL", "METADATA_ONLY"] = "FULL"
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    version: str
    schema_version_id: UUID7
    composition_checksum: str
    prompt_version_id: UUID7
    model_profile_id: UUID7
    evaluation_suite_id: UUID7
    workflow_task_id: UUID7
    workflow_id: str
    status: str
    manifest: dict[str, Any]
    manifest_checksum: str
    gate_summary: dict[str, Any]
    index_config: dict[str, Any]
    notes: str
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7
    lint_findings: tuple[LintFindingResponse, ...] = ()


class ReleaseCandidateListResponse(ContractModel):
    items: tuple[ReleaseCandidateResponse, ...]


class ReleasePublish(ContractModel):
    reason: str = Field(min_length=1, max_length=4000)
    channel: str = Field(default="stable", pattern=r"^[a-z][a-z0-9-]{0,31}$")


class ReleaseResponse(ContractModel):
    manifest_visibility: Literal["FULL", "METADATA_ONLY"] = "FULL"
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    candidate_id: UUID7
    version: str
    status: str
    manifest: dict[str, Any]
    manifest_checksum: str
    schema_version_id: UUID7
    composition_checksum: str
    prompt_version_id: UUID7
    model_profile_id: UUID7
    index_config: dict[str, Any]
    published_at: datetime
    published_by: UUID7
    deprecated_at: datetime | None = None
    deprecation_reason: str | None = None


class ReleaseListResponse(ContractModel):
    items: tuple[ReleaseResponse, ...]


class ReleasePointerSwitch(ContractModel):
    release_id: UUID7
    channel: str = Field(default="stable", pattern=r"^[a-z][a-z0-9-]{0,31}$")
    reason: str = Field(min_length=1, max_length=4000)


class ReleasePointerResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    channel: str
    release_id: UUID7
    version: int
    updated_at: datetime
    updated_by: UUID7


class ReleaseDeprecationCreate(ContractModel):
    reason: str = Field(min_length=1, max_length=4000)
    replacement_release_id: UUID7 | None = None


class QueryCreate(ContractModel):
    question: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    strategy: Literal["KEYWORD", "ATTRIBUTE", "SEMANTIC", "HYBRID"] = "KEYWORD"
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=20, strict=True)
    client_request_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def supported_filters(self) -> "QueryCreate":
        if set(self.filters) - {"predicate_key", "subject_entity_id"} or any(
            not isinstance(value, str) or not value.strip() for value in self.filters.values()
        ):
            raise ValueError("supported string filters: predicate_key, subject_entity_id")
        if self.strategy == "ATTRIBUTE" and not self.filters:
            raise ValueError("ATTRIBUTE requires an explicit supported filter")
        if "subject_entity_id" in self.filters:
            self.filters["subject_entity_id"] = str(UUID(self.filters["subject_entity_id"]))
        return self


class CitationResponse(ContractModel):
    id: UUID7
    release_id: UUID7
    evidence_id: UUID7
    source_version_id: UUID7
    source_anchor_id: UUID7
    claim_id: UUID7 | None = None
    relation_id: UUID7 | None = None
    excerpt: str | None = None
    locator: dict[str, Any]
    status: str


class RetrievalHitResponse(ContractModel):
    object_type: str
    object_id: UUID7
    title: str
    text: str
    ranks: dict[str, int]
    fusion_score: float


QueryAnswerReason = Literal[
    "SUPPORTED_EVIDENCE",
    "NO_MATCHING_KNOWLEDGE",
    "EVIDENCE_UNAVAILABLE",
    "HISTORICAL_RECHECK_SUPPORTED",
    "HISTORICAL_RECHECK_UNAVAILABLE",
]


class QueryAnswerResponse(ContractModel):
    read_checked_at: datetime | None = None
    read_filtered: bool = False
    id: UUID7
    query_session_id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    release_id: UUID7
    question: str
    status: Literal["COMPLETED", "REFUSED", "FAILED"]
    answer_reason: QueryAnswerReason = "EVIDENCE_UNAVAILABLE"
    direct_answer: str
    key_basis: tuple[str, ...]
    uncertainty: str | None = None
    conflicts: tuple[dict[str, Any], ...] = ()
    retrieval_strategy: str
    retrieval_config: dict[str, Any]
    model_profile_id: UUID7
    prompt_version_id: UUID7
    created_at: datetime
    citations: tuple[CitationResponse, ...] = ()
    retrieval_hits: tuple[RetrievalHitResponse, ...] = ()


class GraphEdgeResponse(ContractModel):
    relation_id: UUID7
    relation_type_key: str
    source_entity_id: UUID7
    target_entity_id: UUID7
    depth: int
    evidence_ids: tuple[UUID7, ...] = ()


class GraphNodeResponse(ContractModel):
    id: UUID7
    type_key: str
    normalized_key: str
    display_name: str


class GraphEntityListResponse(ContractModel):
    items: tuple[GraphNodeResponse, ...]


class GraphTraverseResponse(ContractModel):
    release_id: UUID7
    start_entity_id: UUID7
    target_entity_id: UUID7 | None = None
    mode: str
    nodes: tuple[dict[str, Any], ...]
    edges: tuple[GraphEdgeResponse, ...]
    truncated: bool


class EvaluationCompletedEventData(ContractModel):
    evaluation_run_id: UUID7
    target_type: str
    target_id: UUID7
    suite_id: UUID7
    gate_passed: bool
    metrics: dict[str, Any]


class ReleasePublishedEventData(ContractModel):
    release_id: UUID7
    space_id: UUID7
    version: str
    manifest_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ReleasePointerChangedEventData(ContractModel):
    pointer_id: UUID7
    channel: str
    old_release_id: UUID7 | None = None
    new_release_id: UUID7
    reason: str


class ReleaseDeprecatedEventData(ContractModel):
    release_id: UUID7
    reason: str
    replacement_release_id: UUID7 | None = None
