"""M6 Claim/Evidence, Conflict and HumanReview public contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel


class ReviewPolicyCreate(ContractModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    stages: tuple[Literal["ENGINEERING", "EXPERT", "APPROVAL"], ...]
    timeout_seconds: int = Field(ge=60, le=2_592_000)
    escalation_role: Literal["space_admin", "tenant_admin"] = "space_admin"
    allow_batch: bool = False
    batch_limit: int = Field(default=1, ge=1, le=100)
    source_authority_rules: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def high_risk_is_separated(self) -> "ReviewPolicyCreate":
        if self.risk_level == "HIGH" and self.stages != ("ENGINEERING", "EXPERT", "APPROVAL"):
            raise ValueError("HIGH policy requires ENGINEERING, EXPERT, APPROVAL stages")
        if self.allow_batch and self.risk_level != "LOW":
            raise ValueError("only LOW policy may allow batch review")
        return self


class ReviewPolicyResponse(ReviewPolicyCreate):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    version: int
    status: str
    created_at: datetime
    created_by: UUID7


class ClaimResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    candidate_id: UUID7
    schema_version_id: UUID7
    subject_entity_id: UUID7
    predicate_key: str
    object_value: dict[str, Any]
    statement: str
    scope: dict[str, Any]
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    confidence_level: str
    status: str
    provenance: dict[str, Any]
    created_at: datetime
    created_by: UUID7


class ClaimListResponse(ContractModel):
    items: tuple[ClaimResponse, ...]


class EvidenceResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    claim_id: UUID7 | None = None
    relation_candidate_id: UUID7 | None = None
    relation_id: UUID7 | None = None
    source_anchor_id: UUID7
    stance: Literal["SUPPORTS", "OPPOSES", "CONTEXT"]
    excerpt_hash: str
    source_authority: str | None = None
    screenshot_ref: dict[str, Any]
    status: str
    created_at: datetime
    created_by: UUID7


class ConflictResolutionCreate(ContractModel):
    resolution: Literal["RETAIN_BOTH", "CONDITIONAL", "MERGE", "UNRESOLVED", "EXPIRED", "REOPEN"]
    reason: str = Field(min_length=1, max_length=4000)
    conditions: dict[str, Any] = Field(default_factory=dict)


class ConflictResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    cluster_key: str
    kind: str
    severity: str
    blocking: bool
    status: str
    suggested_action: str | None = None
    details: dict[str, Any]
    created_at: datetime
    created_by: UUID7 | None = None


class ConflictListResponse(ContractModel):
    items: tuple[ConflictResponse, ...]


class ReviewCaseCreate(ContractModel):
    target_type: Literal["CLAIM_CANDIDATE", "RELATION_CANDIDATE", "SEMANTIC_PROPOSAL"]
    target_id: UUID7
    policy_id: UUID7
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reason: str = Field(min_length=1, max_length=4000)


class ReviewActionCreate(ContractModel):
    decision: Literal["ACCEPT", "MODIFY", "REJECT", "REQUEST_EVIDENCE", "TRANSFER"]
    reason: str = Field(min_length=1, max_length=4000)
    change_set: dict[str, Any] = Field(default_factory=dict)
    assignee_id: UUID7 | None = None


class ReviewTaskResponse(ContractModel):
    id: UUID7
    stage: str
    status: str
    assignee_id: UUID7 | None = None
    claimed_by: UUID7 | None = None
    due_at: datetime
    escalation_count: int


class ReviewCaseResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    workflow_task_id: UUID7
    workflow_id: str
    target_type: str
    target_id: UUID7
    policy_id: UUID7
    risk_level: str
    status: str
    current_stage: str | None = None
    reason: str
    created_by: UUID7
    created_at: datetime
    updated_at: datetime
    updated_by: UUID7
    tasks: tuple[ReviewTaskResponse, ...] = ()


class ReviewCaseListResponse(ContractModel):
    items: tuple[ReviewCaseResponse, ...]


class ReviewQualityStats(ContractModel):
    total_cases: int
    approved_cases: int
    rejected_cases: int
    modifications: int
    disputes: int
