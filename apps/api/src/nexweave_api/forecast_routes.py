"""Versioned dynamic knowledge endpoints; R1 evidence and release stay separate."""

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Request

from nexweave_api.binding_service import BindingService
from nexweave_api.forecast_knowledge import ForecastKnowledgeService
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.m1_routes import IdempotencyKey, PrincipalDependency, _trace_id
from nexweave_contracts.forecast import (
    BindingCreate,
    BindingEntities,
    BindingList,
    BindingResponse,
    BindingValidation,
    CsvBindingPreview,
    ForecastArtifactResponse,
    ForecastCommand,
    ForecastCreate,
    ForecastKnowledgeContext,
    ForecastKnowledgeRequest,
    ForecastRunList,
    ForecastRunResponse,
    ForecastRuntime,
)

router = APIRouter(prefix="/api/v1", tags=["living-knowledge"])


@router.post(
    "/forecast-artifacts/{artifact_id}/knowledge-context", response_model=ForecastKnowledgeContext
)
async def knowledge_context(
    request: Request,
    artifact_id: UUID,
    body: ForecastKnowledgeRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return await ForecastKnowledgeService(repository(request)).build(
        principal, artifact_id, body, _trace_id(request)
    )


def repository(request: Request) -> ForecastRepository:
    return cast(ForecastRepository, request.app.state.forecast_repository)


@router.post("/spaces/{space_id}/signal-bindings", response_model=BindingResponse, status_code=201)
async def create_binding(
    request: Request,
    space_id: UUID,
    body: BindingCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> dict[str, Any]:
    await BindingService(repository(request), request.app.state.object_storage).validate(
        principal, space_id, body, _trace_id(request)
    )
    return await repository(request).create_binding(
        principal, space_id, body, idempotency_key, _trace_id(request)
    )


@router.get("/spaces/{space_id}/signal-bindings", response_model=BindingList)
async def list_bindings(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return {"items": await repository(request).list_bindings(principal, space_id)}


@router.post(
    "/spaces/{space_id}/forecast-runs", response_model=ForecastRunResponse, status_code=202
)
async def create_run(
    request: Request,
    space_id: UUID,
    body: ForecastCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> dict[str, Any]:
    run = await repository(request).create_run(
        principal, space_id, body, idempotency_key, _trace_id(request)
    )
    return run


@router.get("/spaces/{space_id}/forecast-runs", response_model=ForecastRunList)
async def list_runs(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return {"items": await repository(request).list_runs(principal, space_id)}


@router.get("/forecast-runs/{run_id}", response_model=ForecastRunResponse)
async def get_run(request: Request, run_id: UUID, principal: PrincipalDependency) -> dict[str, Any]:
    return await repository(request).get_run(principal, run_id)


@router.get("/forecast-artifacts/{artifact_id}", response_model=ForecastArtifactResponse)
async def get_artifact(
    request: Request, artifact_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return await repository(request).get_artifact(principal, artifact_id)


@router.post("/forecast-runs/{run_id}/cancel", response_model=ForecastRunResponse)
async def cancel_run(
    request: Request,
    run_id: UUID,
    body: ForecastCommand,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> dict[str, Any]:
    return await repository(request).cancel_run(
        principal, run_id, idempotency_key, body.reason, _trace_id(request)
    )


@router.post("/forecast-runs/{run_id}/retry", response_model=ForecastRunResponse, status_code=202)
async def retry_run(
    request: Request,
    run_id: UUID,
    body: ForecastCommand,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> dict[str, Any]:
    return await repository(request).retry_run(
        principal, run_id, idempotency_key, body.reason, _trace_id(request)
    )


@router.get("/spaces/{space_id}/forecast-runtime", response_model=ForecastRuntime)
async def runtime_status(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return await repository(request).runtime_status(principal, space_id)


@router.get(
    "/spaces/{space_id}/time-series-sources/{source_id}/preview", response_model=CsvBindingPreview
)
async def csv_preview(
    request: Request, space_id: UUID, source_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return await BindingService(repository(request), request.app.state.object_storage).preview(
        principal, space_id, source_id, _trace_id(request)
    )


@router.post("/spaces/{space_id}/signal-bindings/validate", response_model=BindingValidation)
async def validate_binding(
    request: Request, space_id: UUID, body: BindingCreate, principal: PrincipalDependency
) -> dict[str, Any]:
    return await BindingService(repository(request), request.app.state.object_storage).validate(
        principal, space_id, body, _trace_id(request)
    )


@router.get("/spaces/{space_id}/binding-entities", response_model=BindingEntities)
async def binding_entities(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> dict[str, Any]:
    return {"items": await repository(request).binding_entities(principal, space_id)}
