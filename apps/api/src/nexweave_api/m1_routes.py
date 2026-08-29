"""M1 authenticated platform, workspace, governance and object APIs."""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import Response as BinaryResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nexweave_api.errors import ApiProblem, AuthenticationFailed
from nexweave_api.identity import LocalDevIdentityProvider
from nexweave_api.object_storage import S3ObjectStorage
from nexweave_api.repository import PlatformRepository
from nexweave_api.settings import Settings
from nexweave_application import MalwareScannerPort
from nexweave_contracts import (
    AuditLogListResponse,
    ConnectorDefinitionCreate,
    ConnectorDefinitionListResponse,
    ConnectorDefinitionResponse,
    DevSessionRequest,
    DevSessionResponse,
    KnowledgeSpaceResponse,
    ManagedObjectResponse,
    MembershipPolicy,
    ModelProfileCreate,
    ModelProfileListResponse,
    ModelProfileResponse,
    ObjectUploadCreate,
    ObjectUploadSessionResponse,
    OrganizationListResponse,
    PrincipalResponse,
    ProblemDetails,
    PromptVersionCreate,
    PromptVersionListResponse,
    PromptVersionResponse,
    RoleListResponse,
    ServiceIdentityCreate,
    ServiceIdentityListResponse,
    ServiceIdentitySummary,
    SpaceCreate,
    SpaceListResponse,
    SpaceMemberListResponse,
    SpaceMemberResponse,
    SpacePatch,
    UserCreate,
    UserListResponse,
    UserSummary,
)
from nexweave_contracts.identity import RoleDescriptor
from nexweave_domain import ROLE_ACTIONS, DataClassification, Principal, Role, ScanStatus

PROBLEM_RESPONSE = {"model": ProblemDetails, "description": "RFC 9457 problem details"}
router = APIRouter(
    prefix="/api/v1",
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
BEARER_AUTH = HTTPBearer(auto_error=False, scheme_name="OIDC Bearer")


def _repository(request: Request) -> PlatformRepository:
    return cast(PlatformRepository, request.app.state.repository)


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


async def current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER_AUTH)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationFailed()
    settings = _settings(request)
    if settings.identity_provider == "local" and not settings.local_dev_identity_enabled:
        raise AuthenticationFailed("The local identity provider is disabled.")
    token = credentials.credentials.strip()
    if not token:
        raise AuthenticationFailed()
    verified = await request.app.state.identity_provider.verify(token)
    return await _repository(request).resolve_principal(verified)


PrincipalDependency = Annotated[Principal, Depends(current_principal)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]
IfMatch = Annotated[str, Header(alias="If-Match", min_length=4, max_length=64)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageCursor = Annotated[str | None, Query(max_length=512)]


def _paginate(
    items: list[dict[str, Any]], limit: int, cursor: str | None, *, key: str = "id"
) -> dict[str, Any]:
    """Return a stable continuation page anchored to an immutable item identifier."""

    start = 0
    if cursor:
        try:
            padding = "=" * (-len(cursor) % 4)
            anchor = urlsafe_b64decode(f"{cursor}{padding}").decode("utf-8")
        except (Base64Error, UnicodeDecodeError, ValueError) as exc:
            raise ApiProblem(
                400, "INVALID_CURSOR", "Invalid cursor", "The pagination cursor is invalid."
            ) from exc
        try:
            start = next(
                index + 1 for index, item in enumerate(items) if str(item.get(key, "")) == anchor
            )
        except StopIteration as exc:
            raise ApiProblem(
                400,
                "INVALID_CURSOR",
                "Invalid cursor",
                "The pagination anchor is unavailable.",
            ) from exc

    page = items[start : start + limit]
    next_cursor = None
    if page and start + limit < len(items):
        next_cursor = urlsafe_b64encode(str(page[-1][key]).encode()).decode().rstrip("=")
    return {"items": page, "next_cursor": next_cursor}


def _version_from_etag(value: str) -> int:
    if not (value.startswith('"v') and value.endswith('"')):
        raise ApiProblem(
            412,
            "PRECONDITION_FAILED",
            "Invalid precondition",
            "If-Match must contain a strong NEXWEAVE version ETag.",
        )
    try:
        version = int(value[2:-1])
    except ValueError as exc:
        raise ApiProblem(
            412, "PRECONDITION_FAILED", "Invalid precondition", "The ETag is invalid."
        ) from exc
    if version < 1:
        raise ApiProblem(412, "PRECONDITION_FAILED", "Invalid precondition", "The ETag is invalid.")
    return version


def _principal_response(principal: Principal) -> PrincipalResponse:
    return PrincipalResponse(
        actor_type=principal.actor_type,
        actor_id=principal.actor_id,
        tenant_id=principal.tenant_id,
        subject=principal.subject,
        roles=tuple(sorted(principal.tenant_roles, key=str)),
        clearance=principal.clearance,
    )


@router.post("/auth/dev/session", response_model=DevSessionResponse, tags=["identity"])
async def create_dev_session(request: Request, body: DevSessionRequest) -> DevSessionResponse:
    settings = _settings(request)
    provider = request.app.state.identity_provider
    if not settings.local_dev_identity_enabled or not isinstance(
        provider, LocalDevIdentityProvider
    ):
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "Not found", "This endpoint is unavailable.")
    principal = await _repository(request).get_local_principal(body.subject)
    token, expires_in = provider.issue(principal)
    return DevSessionResponse(
        access_token=token,
        token_type="Bearer",  # noqa: S106 - OAuth token type, not a credential
        expires_in=expires_in,
        principal=_principal_response(principal),
    )


@router.get("/auth/me", response_model=PrincipalResponse, tags=["identity"])
async def get_me(principal: PrincipalDependency) -> PrincipalResponse:
    return _principal_response(principal)


@router.get("/roles", response_model=RoleListResponse, tags=["identity"])
async def list_roles(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> RoleListResponse:
    await _repository(request).authorize_tenant(
        principal=principal, action="identity.manage", trace_id=_trace_id(request)
    )
    items = [
        RoleDescriptor(role=role, actions=tuple(sorted(ROLE_ACTIONS[role]))).model_dump(mode="json")
        for role in Role
    ]
    return RoleListResponse.model_validate(_paginate(items, limit, cursor, key="role"))


@router.get("/users", response_model=UserListResponse, tags=["identity"])
async def list_users(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> UserListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="identity.manage", trace_id=_trace_id(request)
    )
    return UserListResponse.model_validate(
        _paginate(await repository.list_users(principal), limit, cursor)
    )


@router.post("/users", response_model=UserSummary, tags=["identity"])
async def create_user(
    request: Request,
    body: UserCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> UserSummary:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="identity.manage", trace_id=_trace_id(request)
    )
    return UserSummary.model_validate(
        await repository.create_user(
            principal=principal,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/organizations", response_model=OrganizationListResponse, tags=["identity"])
async def list_organizations(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> OrganizationListResponse:
    return OrganizationListResponse.model_validate(
        _paginate(await _repository(request).list_organizations(principal), limit, cursor)
    )


@router.post("/service-identities", response_model=ServiceIdentitySummary, tags=["identity"])
async def create_service_identity(
    request: Request,
    body: ServiceIdentityCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ServiceIdentitySummary:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="identity.manage", trace_id=_trace_id(request)
    )
    return ServiceIdentitySummary.model_validate(
        await repository.create_service_identity(
            principal=principal,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/service-identities", response_model=ServiceIdentityListResponse, tags=["identity"])
async def list_service_identities(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> ServiceIdentityListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="identity.manage", trace_id=_trace_id(request)
    )
    return ServiceIdentityListResponse.model_validate(
        _paginate(await repository.list_service_identities(principal), limit, cursor)
    )


@router.post(
    "/spaces",
    response_model=KnowledgeSpaceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace"],
)
async def create_space(
    request: Request,
    body: SpaceCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> KnowledgeSpaceResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="space.create", trace_id=_trace_id(request)
    )
    result = KnowledgeSpaceResponse.model_validate(
        await repository.create_space(
            principal=principal,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
            organization_id=body.organization_id,
            slug=body.slug,
            display_name=body.display_name,
            description=body.description,
            default_classification=body.default_classification,
        )
    )
    response.headers["ETag"] = f'"v{result.version}"'
    return result


@router.get("/spaces", response_model=SpaceListResponse, tags=["workspace"])
async def list_spaces(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> SpaceListResponse:
    return SpaceListResponse.model_validate(
        _paginate(await _repository(request).list_spaces(principal), limit, cursor)
    )


@router.get("/spaces/{space_id}", response_model=KnowledgeSpaceResponse, tags=["workspace"])
async def get_space(
    request: Request, space_id: UUID, principal: PrincipalDependency, response: Response
) -> KnowledgeSpaceResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="space.read", trace_id=_trace_id(request)
    )
    result = KnowledgeSpaceResponse.model_validate(await repository.get_space(space_id))
    response.headers["ETag"] = f'"v{result.version}"'
    return result


@router.patch("/spaces/{space_id}", response_model=KnowledgeSpaceResponse, tags=["workspace"])
async def patch_space(
    request: Request,
    space_id: UUID,
    body: SpacePatch,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> KnowledgeSpaceResponse:
    if not body.model_fields_set:
        raise ApiProblem(422, "VALIDATION_ERROR", "Empty update", "At least one field is required.")
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="space.edit", trace_id=_trace_id(request)
    )
    result = KnowledgeSpaceResponse.model_validate(
        await repository.update_space(
            principal=principal,
            space_id=space_id,
            expected_version=_version_from_etag(if_match),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
            display_name=body.display_name,
            description=body.description,
            default_classification=body.default_classification,
        )
    )
    response.headers["ETag"] = f'"v{result.version}"'
    return result


@router.post(
    "/spaces/{space_id}/archive", response_model=KnowledgeSpaceResponse, tags=["workspace"]
)
async def archive_space(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> KnowledgeSpaceResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="space.archive", trace_id=_trace_id(request)
    )
    result = KnowledgeSpaceResponse.model_validate(
        await repository.archive_space(
            principal=principal,
            space_id=space_id,
            expected_version=_version_from_etag(if_match),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )
    response.headers["ETag"] = f'"v{result.version}"'
    return result


@router.get(
    "/spaces/{space_id}/members", response_model=SpaceMemberListResponse, tags=["workspace"]
)
async def list_space_members(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> SpaceMemberListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="member.read", trace_id=_trace_id(request)
    )
    return SpaceMemberListResponse.model_validate(
        _paginate(await repository.list_members(principal, space_id), limit, cursor)
    )


@router.put(
    "/spaces/{space_id}/members/{subject_id}",
    response_model=SpaceMemberResponse,
    tags=["workspace"],
)
async def grant_space_member(
    request: Request,
    space_id: UUID,
    subject_id: UUID,
    body: MembershipPolicy,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> SpaceMemberResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="member.grant", trace_id=_trace_id(request)
    )
    return SpaceMemberResponse.model_validate(
        await repository.grant_member(
            principal=principal,
            space_id=space_id,
            subject_id=subject_id,
            subject_type=body.subject_type,
            roles=body.roles,
            clearance=body.clearance,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.delete(
    "/spaces/{space_id}/members/{subject_id}",
    response_model=SpaceMemberResponse,
    tags=["workspace"],
)
async def revoke_space_member(
    request: Request,
    space_id: UUID,
    subject_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> SpaceMemberResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="member.revoke", trace_id=_trace_id(request)
    )
    return SpaceMemberResponse.model_validate(
        await repository.revoke_member(
            principal=principal,
            space_id=space_id,
            subject_id=subject_id,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/audit-logs", response_model=AuditLogListResponse, tags=["administration"])
async def list_audit_logs(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> AuditLogListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="audit.read", trace_id=_trace_id(request)
    )
    return AuditLogListResponse.model_validate(
        _paginate(await repository.list_audit_logs(principal), limit, cursor)
    )


@router.post("/model-profiles", response_model=ModelProfileResponse, tags=["administration"])
async def create_model_profile(
    request: Request,
    body: ModelProfileCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ModelProfileResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return ModelProfileResponse.model_validate(
        await repository.create_governance_object(
            kind="model_profile",
            principal=principal,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/model-profiles", response_model=ModelProfileListResponse, tags=["administration"])
async def list_model_profiles(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> ModelProfileListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return ModelProfileListResponse.model_validate(
        _paginate(
            await repository.list_governance_objects("model_profile", principal), limit, cursor
        )
    )


@router.post("/prompt-versions", response_model=PromptVersionResponse, tags=["administration"])
async def create_prompt_version(
    request: Request,
    body: PromptVersionCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> PromptVersionResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return PromptVersionResponse.model_validate(
        await repository.create_governance_object(
            kind="prompt_version",
            principal=principal,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get("/prompt-versions", response_model=PromptVersionListResponse, tags=["administration"])
async def list_prompt_versions(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> PromptVersionListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return PromptVersionListResponse.model_validate(
        _paginate(
            await repository.list_governance_objects("prompt_version", principal), limit, cursor
        )
    )


@router.post(
    "/connector-definitions", response_model=ConnectorDefinitionResponse, tags=["administration"]
)
async def create_connector_definition(
    request: Request,
    body: ConnectorDefinitionCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ConnectorDefinitionResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return ConnectorDefinitionResponse.model_validate(
        await repository.create_governance_object(
            kind="connector_definition",
            principal=principal,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    )


@router.get(
    "/connector-definitions",
    response_model=ConnectorDefinitionListResponse,
    tags=["administration"],
)
async def list_connector_definitions(
    request: Request,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
) -> ConnectorDefinitionListResponse:
    repository = _repository(request)
    await repository.authorize_tenant(
        principal=principal, action="governance.manage", trace_id=_trace_id(request)
    )
    return ConnectorDefinitionListResponse.model_validate(
        _paginate(
            await repository.list_governance_objects("connector_definition", principal),
            limit,
            cursor,
        )
    )


@router.post(
    "/spaces/{space_id}/object-uploads",
    response_model=ObjectUploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["objects"],
)
async def create_object_upload(
    request: Request,
    space_id: UUID,
    body: ObjectUploadCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ObjectUploadSessionResponse:
    settings, repository = _settings(request), _repository(request)
    if body.expected_size > settings.object_upload_max_bytes:
        raise ApiProblem(
            413,
            "VALIDATION_ERROR",
            "Upload too large",
            "The object exceeds the configured upload limit.",
        )
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="object.upload",
        trace_id=_trace_id(request),
        classification=body.classification,
    )
    return ObjectUploadSessionResponse.model_validate(
        await repository.create_upload_session(
            principal=principal,
            space_id=space_id,
            payload=body.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
            ttl_seconds=settings.object_upload_session_seconds,
        )
    )


@router.put(
    "/object-uploads/{upload_id}/content",
    response_model=ManagedObjectResponse,
    tags=["objects"],
)
async def upload_object_content(
    request: Request,
    upload_id: UUID,
    principal: PrincipalDependency,
    content_type: Annotated[str | None, Header(alias="Content-Type")] = None,
) -> ManagedObjectResponse:
    repository = _repository(request)
    session = await repository.get_upload_session(upload_id)
    classification = DataClassification(session["classification"])
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(session["space_id"]),
        action="object.upload",
        trace_id=_trace_id(request),
        classification=classification,
    )
    if session["status"] == "COMPLETED":
        return _managed_object(await repository.get_managed_object(upload_id))
    if session["status"] not in {"INITIATED", "UPLOADING"}:
        raise ApiProblem(
            409,
            "STATE_TRANSITION_NOT_ALLOWED",
            "Upload unavailable",
            "The upload session is no longer writable.",
        )
    content = await request.body()
    if len(content) != int(session["expected_size"]):
        raise ApiProblem(
            422,
            "VALIDATION_ERROR",
            "Size mismatch",
            "The uploaded size does not match the controlled session.",
        )
    if content_type != session["content_type"]:
        raise ApiProblem(
            422,
            "VALIDATION_ERROR",
            "Content type mismatch",
            "The content type does not match the controlled session.",
        )
    checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
    key = (
        f"managed/v1/{session['tenant_id']}/{session['space_id']}/{upload_id}/"
        f"{checksum.removeprefix('sha256:')}"
    )
    storage = cast(S3ObjectStorage, request.app.state.object_storage)
    info = await storage.put_if_absent(
        key=key, content=content, content_type=content_type, checksum_sha256=checksum
    )
    scanner = cast(MalwareScannerPort, request.app.state.malware_scanner)
    scan_status = await scanner.scan(content=content, content_type=content_type)
    result = await repository.complete_upload(
        principal=principal,
        upload_id=upload_id,
        info=info,
        filename=session["filename"],
        classification=classification,
        scan_status=scan_status,
        trace_id=_trace_id(request),
    )
    return _managed_object(result)


def _managed_object(value: dict[str, Any]) -> ManagedObjectResponse:
    return ManagedObjectResponse.model_validate(
        {key: value.get(key) for key in ManagedObjectResponse.model_fields}
    )


@router.get("/objects/{object_id}", response_model=ManagedObjectResponse, tags=["objects"])
async def get_object_metadata(
    request: Request, object_id: UUID, principal: PrincipalDependency
) -> ManagedObjectResponse:
    repository = _repository(request)
    value = await repository.get_managed_object(object_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(value["space_id"]),
        action="object.download",
        trace_id=_trace_id(request),
        classification=DataClassification(value["classification"]),
    )
    return _managed_object(value)


@router.get("/objects/{object_id}/content", tags=["objects"])
async def download_object_content(
    request: Request, object_id: UUID, principal: PrincipalDependency
) -> BinaryResponse:
    repository = _repository(request)
    value = await repository.get_managed_object(object_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(value["space_id"]),
        action="object.download",
        trace_id=_trace_id(request),
        classification=DataClassification(value["classification"]),
    )
    if ScanStatus(value["scan_status"]) is not ScanStatus.CLEAN:
        raise ApiProblem(
            409,
            "STATE_TRANSITION_NOT_ALLOWED",
            "Object unavailable",
            "The object has not passed the scan gate.",
        )
    storage = cast(S3ObjectStorage, request.app.state.object_storage)
    content = await storage.get(key=value["object_key"])
    return BinaryResponse(
        content=content,
        media_type=value["content_type"],
        headers={
            "Content-Disposition": "attachment",
            "X-Content-Checksum": value["checksum"],
        },
    )
