"""Authenticated M6 Claim/Evidence, conflict and HumanReview APIs."""
# ruff: noqa: E501

from __future__ import annotations

from hashlib import sha256
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, status

from nexweave_api.m1_routes import IdempotencyKey, PrincipalDependency, _trace_id
from nexweave_api.review_repository import ReviewRepository
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_contracts import (
    ClaimListResponse,
    ConflictListResponse,
    ConflictResolutionCreate,
    ConflictResponse,
    EvidenceResponse,
    ReviewActionCreate,
    ReviewCaseCreate,
    ReviewCaseListResponse,
    ReviewCaseResponse,
    ReviewPolicyCreate,
    ReviewPolicyResponse,
    ReviewQualityStats,
)
from nexweave_domain import WorkflowType

router = APIRouter(prefix="/api/v1", tags=["claims", "conflicts", "reviews"])


def _repository(request: Request) -> ReviewRepository:
    return cast(ReviewRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/review-policies",
    response_model=ReviewPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review_policy(
    request: Request, space_id: UUID, body: ReviewPolicyCreate, principal: PrincipalDependency
) -> ReviewPolicyResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="review.policy.manage",
        trace_id=_trace_id(request),
    )
    return ReviewPolicyResponse.model_validate(
        await repository.create_review_policy(
            principal=principal,
            space_id=space_id,
            payload=body.model_dump(mode="json"),
            trace_id=_trace_id(request),
        )
    )


@router.get("/spaces/{space_id}/review-policies", response_model=list[ReviewPolicyResponse])
async def list_review_policies(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> list[ReviewPolicyResponse]:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="review.read", trace_id=_trace_id(request)
    )
    return [
        ReviewPolicyResponse.model_validate(item)
        for item in await repository.list_review_policies(principal=principal, space_id=space_id)
    ]


@router.get("/spaces/{space_id}/claims", response_model=ClaimListResponse)
async def list_claims(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ClaimListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="claim.read", trace_id=_trace_id(request)
    )
    return ClaimListResponse.model_validate(
        {"items": await repository.list_claims(principal=principal, space_id=space_id)}
    )


@router.get("/claims/{claim_id}/evidence", response_model=list[EvidenceResponse])
async def list_claim_evidence(
    request: Request, claim_id: UUID, principal: PrincipalDependency
) -> list[EvidenceResponse]:
    repository = _repository(request)
    evidence = await repository.list_evidence(principal=principal, claim_id=claim_id)
    if not evidence:
        return []
    # Claim scope is checked through the authoritative claim record before returning evidence.
    claims = await repository.list_claims(
        principal=principal, space_id=UUID(str(evidence[0]["space_id"]))
    )
    if not any(str(item["id"]) == str(claim_id) for item in claims):
        return []
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(evidence[0]["space_id"])),
        action="claim.read",
        trace_id=_trace_id(request),
    )
    return [EvidenceResponse.model_validate(item) for item in evidence]


@router.post(
    "/spaces/{space_id}/review-cases",
    response_model=ReviewCaseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_review_case(
    request: Request,
    space_id: UUID,
    body: ReviewCaseCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReviewCaseResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="review.create", trace_id=trace_id
    )
    policy = await repository.get_review_policy(principal=principal, policy_id=body.policy_id)
    business_key = (
        f"{body.target_type}:{body.target_id}:{sha256(idempotency_key.encode()).hexdigest()[:16]}"
    )
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.HUMAN_REVIEW.value,
            "business_key": business_key,
            "display_name": "Governed human review",
            "input_refs": {
                "target_type": body.target_type,
                "target_id": str(body.target_id),
                "policy_id": str(body.policy_id),
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    case = await repository.create_review_case(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        workflow_task_id=UUID(str(task["id"])),
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.human-review.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.HUMAN_REVIEW.value,
            "task_id": str(task["id"]),
            "review_case_id": str(case["id"]),
            "actor_id": str(principal.actor_id),
            "trace_id": trace_id,
            "approval_timeout_seconds": int(policy["timeout_seconds"]),
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    return ReviewCaseResponse.model_validate(case)


@router.get("/spaces/{space_id}/review-cases", response_model=ReviewCaseListResponse)
async def list_review_cases(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ReviewCaseListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="review.read", trace_id=_trace_id(request)
    )
    return ReviewCaseListResponse.model_validate(
        {"items": await repository.list_review_cases(principal=principal, space_id=space_id)}
    )


@router.post("/review-cases/{case_id}/tasks/{task_id}/actions", response_model=ReviewCaseResponse)
async def act_on_review(
    request: Request,
    case_id: UUID,
    task_id: UUID,
    body: ReviewActionCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReviewCaseResponse:
    repository = _repository(request)
    current = await repository.get_review_case(principal=principal, case_id=case_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(current["space_id"])),
        action="review.act",
        trace_id=_trace_id(request),
    )
    updated = await repository.act_on_review(
        principal=principal,
        case_id=case_id,
        task_id=task_id,
        payload=body.model_dump(mode="json"),
        trace_id=_trace_id(request),
    )
    if updated["status"] in {"APPROVED", "REJECTED"}:
        await _gateway(request).command(
            workflow_id=str(updated["workflow_id"]),
            command_id=idempotency_key,
            action="APPROVE" if updated["status"] == "APPROVED" else "REJECT",
            reason=body.reason,
            actor_id=str(principal.actor_id),
        )
    return ReviewCaseResponse.model_validate(updated)


@router.get("/spaces/{space_id}/conflicts", response_model=ConflictListResponse)
async def list_conflicts(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ConflictListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="conflict.read", trace_id=_trace_id(request)
    )
    return ConflictListResponse.model_validate(
        {"items": await repository.list_conflicts(principal=principal, space_id=space_id)}
    )


@router.post("/spaces/{space_id}/conflicts/detect", response_model=ConflictListResponse)
async def detect_conflicts(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ConflictListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="conflict.resolve",
        trace_id=_trace_id(request),
    )
    return ConflictListResponse.model_validate(
        {
            "items": await repository.materialize_conflicts(
                principal=principal, space_id=space_id, trace_id=_trace_id(request)
            )
        }
    )


@router.post("/conflicts/{conflict_id}/decisions", response_model=ConflictResponse)
async def resolve_conflict(
    request: Request,
    conflict_id: UUID,
    body: ConflictResolutionCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ConflictResponse:
    repository = _repository(request)
    current = await repository.get_conflict(principal=principal, conflict_id=conflict_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(current["space_id"])),
        action="conflict.resolve",
        trace_id=_trace_id(request),
    )
    resolved = await repository.resolve_conflict(
        principal=principal,
        conflict_id=conflict_id,
        payload=body.model_dump(mode="json"),
        trace_id=_trace_id(request),
    )
    return ConflictResponse.model_validate(resolved)


@router.get("/spaces/{space_id}/review-quality", response_model=ReviewQualityStats)
async def review_quality(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ReviewQualityStats:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="review.read", trace_id=_trace_id(request)
    )
    return ReviewQualityStats.model_validate(
        await repository.review_quality_stats(principal=principal, space_id=space_id)
    )
