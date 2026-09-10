"""Authenticated M8 read-only Connector and Obsidian exchange APIs."""
# ruff: noqa: E501

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, status

from nexweave_api.integration_repository import IntegrationRepository
from nexweave_api.m1_routes import IdempotencyKey, PrincipalDependency, _trace_id
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_contracts import (
    ConnectorInstanceCreate,
    ConnectorInstanceListResponse,
    ConnectorInstanceResponse,
    ConnectorSyncRunCreate,
    ConnectorSyncRunResponse,
    ObsidianExportResponse,
    ObsidianImportCreate,
    ObsidianImportResponse,
)

router = APIRouter(prefix="/api/v1", tags=["connectors", "obsidian"])


def _repository(request: Request) -> IntegrationRepository:
    return cast(IntegrationRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/connector-instances",
    response_model=ConnectorInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connector_instance(
    request: Request,
    space_id: UUID,
    body: ConnectorInstanceCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ConnectorInstanceResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="governance.manage",
        trace_id=_trace_id(request),
        classification=body.classification,
    )
    return ConnectorInstanceResponse.model_validate(
        await repository.create_connector_instance(
            principal=principal,
            space_id=space_id,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/spaces/{space_id}/connector-instances", response_model=ConnectorInstanceListResponse)
async def list_connector_instances(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> ConnectorInstanceListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="governance.manage",
        trace_id=_trace_id(request),
    )
    return ConnectorInstanceListResponse.model_validate(
        {"items": await repository.list_connector_instances(principal=principal, space_id=space_id)}
    )


@router.post(
    "/spaces/{space_id}/connector-instances/{instance_id}/sync-runs",
    response_model=ConnectorSyncRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_sync_run(
    request: Request,
    space_id: UUID,
    instance_id: UUID,
    body: ConnectorSyncRunCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ConnectorSyncRunResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    instance = await repository.get_connector_instance(principal=principal, instance_id=instance_id)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="source.upload",
        trace_id=trace_id,
        classification=instance["classification"],
    )
    run = await repository.create_connector_sync_run(
        principal=principal,
        space_id=space_id,
        instance_id=instance_id,
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.connector-sync.v2",
        workflow_id=str(run["workflow_id"]),
        payload={
            "connector_sync_run_id": str(run["id"]),
            "task_id": str(run["workflow_task_id"]),
            "trace_id": trace_id,
            "workflow_task_queue": request.app.state.settings.temporal_workflow_task_queue,
            "activity_task_queue": request.app.state.settings.temporal_activity_task_queue,
            "parser_activity_task_queue": request.app.state.settings.temporal_parser_activity_task_queue,
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(run["workflow_task_id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    return ConnectorSyncRunResponse.model_validate(
        await repository.mark_connector_sync_started(
            run_id=UUID(str(run["id"])),
            temporal_run_id=execution.run_id,
            actor_id=principal.actor_id,
        )
    )


@router.get("/connector-sync-runs/{run_id}", response_model=ConnectorSyncRunResponse)
async def get_sync_run(
    request: Request, run_id: UUID, principal: PrincipalDependency
) -> ConnectorSyncRunResponse:
    repository = _repository(request)
    run = await repository.get_connector_sync_run(principal=principal, run_id=run_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(run["space_id"])),
        action="source.read",
        trace_id=_trace_id(request),
    )
    return ConnectorSyncRunResponse.model_validate(run)


@router.post(
    "/wiki/pages/{page_id}/obsidian-exports",
    response_model=ObsidianExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def export_obsidian_page(
    request: Request, page_id: UUID, principal: PrincipalDependency
) -> ObsidianExportResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return ObsidianExportResponse.model_validate(
        await repository.export_obsidian_page(
            principal=principal, page_id=page_id, trace_id=_trace_id(request)
        )
    )


@router.post(
    "/spaces/{space_id}/obsidian-imports",
    response_model=ObsidianImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_obsidian_page(
    request: Request,
    space_id: UUID,
    body: ObsidianImportCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ObsidianImportResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="page.edit", trace_id=_trace_id(request)
    )
    return ObsidianImportResponse.model_validate(
        await repository.import_obsidian_markdown(
            principal=principal,
            space_id=space_id,
            markdown=body.markdown,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )
