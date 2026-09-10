"""Authenticated M4 SchemaVersion APIs; semantic model is never a second authority."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from nexweave_api.errors import ApiProblem
from nexweave_api.m1_routes import (
    PROBLEM_RESPONSE,
    IdempotencyKey,
    IfMatch,
    PrincipalDependency,
    _trace_id,
    _version_from_etag,
)
from nexweave_api.semantic_repository import SemanticRepository
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_contracts import (
    CompositionReportResponse,
    DomainPackInstallationCreate,
    DomainPackInstallationResponse,
    DomainPackRegisterRequest,
    DomainPackRevocationImportResponse,
    DomainPackRevocationListV1Alpha1,
    DomainPackRollbackCreate,
    DomainPackTrustKeyCreate,
    DomainPackTrustKeyResponse,
    DomainPackVersionListResponse,
    DomainPackVersionResponse,
    SchemaComposeRequest,
    SchemaCreate,
    SchemaListResponse,
    SchemaVersionCreate,
    SchemaVersionResponse,
)
from nexweave_domain import Principal, WorkflowType

router = APIRouter(
    prefix="/api/v1",
    tags=["schemas"],
    responses={
        400: PROBLEM_RESPONSE,
        401: PROBLEM_RESPONSE,
        403: PROBLEM_RESPONSE,
        404: PROBLEM_RESPONSE,
        409: PROBLEM_RESPONSE,
        412: PROBLEM_RESPONSE,
        422: PROBLEM_RESPONSE,
    },
)


def _repository(request: Request) -> SemanticRepository:
    return cast(SemanticRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/schemas",
    response_model=SchemaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schema(
    request: Request,
    space_id: UUID,
    body: SchemaCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> SchemaVersionResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="schema.edit", trace_id=_trace_id(request)
    )
    result = await repository.create_schema(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SchemaVersionResponse.model_validate(result)


@router.get("/spaces/{space_id}/schemas", response_model=SchemaListResponse)
async def list_schemas(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> SchemaListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="schema.read", trace_id=_trace_id(request)
    )
    return SchemaListResponse.model_validate(
        {"items": await repository.list_schemas(principal=principal, space_id=space_id)}
    )


@router.post(
    "/schemas/{schema_id}/versions",
    response_model=SchemaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schema_version(
    request: Request,
    schema_id: UUID,
    body: SchemaVersionCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> SchemaVersionResponse:
    repository = _repository(request)
    existing = await repository.get_schema_version_chain_space(
        principal=principal, schema_id=schema_id
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(existing)),
        action="schema.edit",
        trace_id=_trace_id(request),
    )
    result = await repository.create_schema_version(
        principal=principal,
        schema_id=schema_id,
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SchemaVersionResponse.model_validate(result)


@router.post("/schemas/{schema_id}/compose", response_model=CompositionReportResponse)
async def compose_schema(
    request: Request,
    schema_id: UUID,
    body: SchemaComposeRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> CompositionReportResponse:
    repository = _repository(request)
    space_id = await repository.get_schema_version_chain_space(
        principal=principal, schema_id=schema_id
    )
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="schema.edit",
        trace_id=_trace_id(request),
    )
    return CompositionReportResponse.model_validate(
        await repository.compose_schema_candidate(
            principal=principal,
            schema_id=schema_id,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get(
    "/schemas/{schema_id}/versions/{semantic_version}", response_model=SchemaVersionResponse
)
@router.get(
    "/schemas/{schema_id}/versions/{semantic_version}/semantic-model",
    response_model=SchemaVersionResponse,
)
async def get_schema(
    request: Request,
    schema_id: UUID,
    semantic_version: str,
    principal: PrincipalDependency,
    response: Response,
) -> SchemaVersionResponse:
    repository = _repository(request)
    result = await repository.get_schema_version(
        principal=principal, schema_id=schema_id, semantic_version=semantic_version
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(result["space_id"])),
        action="schema.read",
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SchemaVersionResponse.model_validate(result)


@router.post(
    "/schemas/{schema_id}/versions/{semantic_version}/validate",
    response_model=CompositionReportResponse,
)
async def validate_schema(
    request: Request, schema_id: UUID, semantic_version: str, principal: PrincipalDependency
) -> CompositionReportResponse:
    repository = _repository(request)
    schema = await repository.get_schema_version(
        principal=principal, schema_id=schema_id, semantic_version=semantic_version
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(schema["space_id"])),
        action="schema.validate",
        trace_id=_trace_id(request),
    )
    return CompositionReportResponse.model_validate(
        await repository.validate_schema(
            principal=principal,
            schema_id=schema_id,
            semantic_version=semantic_version,
            trace_id=_trace_id(request),
        )
    )


@router.get("/schema-composition-reports/{report_id}", response_model=CompositionReportResponse)
async def get_composition_report(
    request: Request, report_id: UUID, principal: PrincipalDependency
) -> CompositionReportResponse:
    repository = _repository(request)
    report = await repository.get_composition_report(principal=principal, report_id=report_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(report["space_id"])),
        action="schema.read",
        trace_id=_trace_id(request),
    )
    return CompositionReportResponse.model_validate(report)


@router.post(
    "/schemas/{schema_id}/versions/{semantic_version}/publish", response_model=SchemaVersionResponse
)
async def publish_schema(
    request: Request,
    schema_id: UUID,
    semantic_version: str,
    principal: PrincipalDependency,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> SchemaVersionResponse:
    repository = _repository(request)
    schema = await repository.get_schema_version(
        principal=principal, schema_id=schema_id, semantic_version=semantic_version
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(schema["space_id"])),
        action="schema.publish",
        trace_id=_trace_id(request),
    )
    result = await repository.publish_schema(
        principal=principal,
        schema_id=schema_id,
        semantic_version=semantic_version,
        expected_version=_version_from_etag(if_match),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SchemaVersionResponse.model_validate(result)


@router.post(
    "/schemas/{schema_id}/versions/{semantic_version}/deprecate",
    response_model=SchemaVersionResponse,
)
async def deprecate_schema(
    request: Request,
    schema_id: UUID,
    semantic_version: str,
    principal: PrincipalDependency,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> SchemaVersionResponse:
    repository = _repository(request)
    schema = await repository.get_schema_version(
        principal=principal, schema_id=schema_id, semantic_version=semantic_version
    )
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(schema["space_id"])),
        action="schema.publish",
        trace_id=_trace_id(request),
    )
    result = await repository.deprecate_schema(
        principal=principal,
        schema_id=schema_id,
        semantic_version=semantic_version,
        expected_version=_version_from_etag(if_match),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SchemaVersionResponse.model_validate(result)


@router.get("/domain-packs", response_model=DomainPackVersionListResponse)
async def list_domain_packs(
    request: Request, principal: PrincipalDependency
) -> DomainPackVersionListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="pack.read", trace_id=_trace_id(request)
    )
    return DomainPackVersionListResponse.model_validate(
        {"items": await repository.list_domain_pack_versions(principal=principal)}
    )


@router.post(
    "/domain-pack-trust-keys",
    response_model=DomainPackTrustKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_domain_pack_trust_key(
    request: Request,
    body: DomainPackTrustKeyCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackTrustKeyResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return DomainPackTrustKeyResponse.model_validate(
        await repository.register_domain_pack_trust_key(
            principal=principal,
            payload=body.model_dump(mode="python"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.post(
    "/domain-packs",
    response_model=DomainPackVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_domain_pack(
    request: Request,
    body: DomainPackRegisterRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackVersionResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return DomainPackVersionResponse.model_validate(
        await repository.register_domain_pack(
            principal=principal,
            manifest=body.manifest,
            contents=body.contents,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.post(
    "/domain-pack-revocations/import",
    response_model=DomainPackRevocationImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_domain_pack_revocations(
    request: Request,
    body: DomainPackRevocationListV1Alpha1,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackRevocationImportResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return DomainPackRevocationImportResponse.model_validate(
        await repository.import_pack_revocation_list(
            principal=principal,
            document=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.post(
    "/spaces/{space_id}/domain-pack-installations",
    response_model=DomainPackInstallationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def install_domain_pack(
    request: Request,
    space_id: UUID,
    body: DomainPackInstallationCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackInstallationResponse:
    repository = _repository(request)
    trace_id = _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="pack.install", trace_id=trace_id
    )
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.DOMAIN_PACK_INSTALL.value,
            "business_key": (
                f"{body.operation.lower()}:{body.domain_pack_version_id}:"
                f"{body.schema_definition_id}:"
                f"{body.semantic_version}"
            ),
            "display_name": "Install declarative Domain Pack",
            "input_refs": {
                "domain_pack_version_id": str(body.domain_pack_version_id),
                "schema_definition_id": str(body.schema_definition_id),
                "semantic_version": body.semantic_version,
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    installation = await repository.create_installation(
        principal=principal,
        space_id=space_id,
        domain_pack_version_id=UUID(str(body.domain_pack_version_id)),
        schema_definition_id=UUID(str(body.schema_definition_id)),
        requested_semantic_version=body.semantic_version,
        operation=body.operation,
        previous_installation_id=UUID(str(body.previous_installation_id))
        if body.previous_installation_id
        else None,
        workflow_task_id=UUID(str(task["id"])),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.domain-pack-install.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.DOMAIN_PACK_INSTALL.value,
            "task_id": str(task["id"]),
            "installation_id": str(installation["id"]),
            "actor_id": str(principal.actor_id),
            "trace_id": trace_id,
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    installation = await repository.mark_installation_started(
        installation_id=UUID(str(installation["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
    )
    return DomainPackInstallationResponse.model_validate(installation)


@router.get(
    "/domain-pack-installations/{installation_id}",
    response_model=DomainPackInstallationResponse,
)
async def get_domain_pack_installation(
    request: Request, installation_id: UUID, principal: PrincipalDependency
) -> DomainPackInstallationResponse:
    repository = _repository(request)
    installation = await repository.get_installation(installation_id=installation_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(installation["space_id"])),
        action="pack.read",
        trace_id=_trace_id(request),
    )
    return DomainPackInstallationResponse.model_validate(installation)


@router.post(
    "/spaces/{space_id}/domain-pack-installations/{installation_id}/disable",
    response_model=DomainPackInstallationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def disable_domain_pack(
    request: Request,
    space_id: UUID,
    installation_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackInstallationResponse:
    return await _create_control_installation(
        request=request,
        space_id=space_id,
        target_installation_id=installation_id,
        operation="DISABLE",
        principal=principal,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/spaces/{space_id}/domain-pack-installations/rollback",
    response_model=DomainPackInstallationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rollback_domain_pack(
    request: Request,
    space_id: UUID,
    body: DomainPackRollbackCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DomainPackInstallationResponse:
    return await _create_control_installation(
        request=request,
        space_id=space_id,
        target_installation_id=UUID(str(body.target_installation_id)),
        operation="ROLLBACK",
        principal=principal,
        idempotency_key=idempotency_key,
    )


async def _create_control_installation(
    *,
    request: Request,
    space_id: UUID,
    target_installation_id: UUID,
    operation: str,
    principal: Principal,
    idempotency_key: str,
) -> DomainPackInstallationResponse:
    repository = _repository(request)
    trace_id = _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="pack.rollback", trace_id=trace_id
    )
    target = await repository.get_installation(installation_id=target_installation_id)
    if UUID(str(target["space_id"])) != space_id:
        raise ApiProblem(
            404,
            "RESOURCE_NOT_FOUND",
            "Pack installation not found",
            "The target installation is not available in this space.",
        )
    semantic_version = str(target["requested_semantic_version"])
    if operation == "DISABLE":
        base_version = semantic_version.split("-", maxsplit=1)[0]
        semantic_version = f"{base_version}-disable.{str(target_installation_id)[:8]}"
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.DOMAIN_PACK_INSTALL.value,
            "business_key": f"{operation.lower()}:{target_installation_id}",
            "display_name": f"{operation.title()} declarative Domain Pack",
            "input_refs": {
                "target_installation_id": str(target_installation_id),
                "operation": operation,
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    installation = await repository.create_installation(
        principal=principal,
        space_id=space_id,
        domain_pack_version_id=UUID(str(target["domain_pack_version_id"])),
        schema_definition_id=UUID(str(target["schema_definition_id"])),
        requested_semantic_version=semantic_version,
        operation=operation,
        previous_installation_id=target_installation_id,
        workflow_task_id=UUID(str(task["id"])),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.domain-pack-install.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.DOMAIN_PACK_INSTALL.value,
            "task_id": str(task["id"]),
            "installation_id": str(installation["id"]),
            "actor_id": str(principal.actor_id),
            "trace_id": trace_id,
        },
    )
    await repository.mark_workflow_started(
        task_id=UUID(str(task["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
        trace_id=trace_id,
    )
    installation = await repository.mark_installation_started(
        installation_id=UUID(str(installation["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
    )
    return DomainPackInstallationResponse.model_validate(installation)
