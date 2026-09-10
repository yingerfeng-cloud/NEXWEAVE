"""M7 quality, immutable Release, graph and trusted-query contracts."""

from datetime import datetime
from typing import Any, Literal

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
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationSuiteCreate(ContractModel):
    schema_version_id: UUID7
    suite_key: str = Field(pattern=r"^[a-z][a-z0-9.-]{1,62}/[a-z][a-z0-9-]{0,62}$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    cases: tuple[EvaluationCaseInput, ...] = Field(min_length=1, max_length=500)
    minimum_pass_rate: int = Field(default=100, ge=0, le=100)


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
    retrieval_strategy: Literal["KEYWORD", "ATTRIBUTE", "SEMANTIC", "HYBRID"] = "HYBRID"
    retrieval_config: dict[str, Any] = Field(default_factory=dict)


class EvaluationCaseResult(ContractModel):
    case_key: str
    case_type: str
    passed: bool
    answer_status: str
    matched_claim_ids: tuple[UUID7, ...] = ()
    error_code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunResponse(ContractModel):
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
    index_config: dict[str, Any] = Field(default_factory=lambda: {"version": "m7-r1"})
    notes: str = Field(default="", max_length=4000)

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
    question: str = Field(min_length=1, max_length=4000)
    strategy: Literal["KEYWORD", "ATTRIBUTE", "SEMANTIC", "HYBRID"] = "HYBRID"
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=20)
    client_request_id: str = Field(min_length=1, max_length=128)


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
