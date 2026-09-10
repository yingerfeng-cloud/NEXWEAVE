"""Authenticated M5 Compile and Wiki draft APIs."""

from hashlib import sha256
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from nexweave_api.errors import ApiProblem
from nexweave_api.knowledge_repository import KnowledgeRepository
from nexweave_api.m1_routes import (
    PROBLEM_RESPONSE,
    IdempotencyKey,
    IfMatch,
    PrincipalDependency,
    _trace_id,
    _version_from_etag,
)
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_contracts import (
    CompileJobCreate,
    CompileJobListResponse,
    CompileJobResponse,
    KnowledgeEntityListResponse,
    WikiCommentCreate,
    WikiCommentResponse,
    WikiDiffResponse,
    WikiLinkGraphResponse,
    WikiPageEdit,
    WikiPageListResponse,
    WikiPageResponse,
    WikiPageVersionListResponse,
    WikiPageVersionResponse,
)
from nexweave_domain import WorkflowType

router = APIRouter(
    prefix="/api/v1",
    tags=["compile", "wiki"],
    responses={code: PROBLEM_RESPONSE for code in (400, 401, 403, 404, 409, 412, 422)},
)


def _repository(request: Request) -> KnowledgeRepository:
    return cast(KnowledgeRepository, request.app.state.repository)


def _gateway(request: Request) -> TemporalWorkflowGateway:
    return cast(TemporalWorkflowGateway, request.app.state.workflow_gateway)


@router.post(
    "/spaces/{space_id}/compile-jobs",
    response_model=CompileJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_compile_job(
    request: Request,
    space_id: UUID,
    body: CompileJobCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> CompileJobResponse:
    repository, trace_id = _repository(request), _trace_id(request)
    await repository.authorize_space(
        principal=principal, space_id=space_id, action="compile.create", trace_id=trace_id
    )
    business_key = (
        f"{body.schema_version_id}:"
        f"{','.join(sorted(str(value) for value in body.source_version_ids))}:"
        f"{body.prompt_version_id}:{body.model_profile_id}:{body.mode}:"
        f"{sha256(idempotency_key.encode()).hexdigest()[:16]}"
    )
    task = await repository.create_workflow_task(
        principal=principal,
        space_id=space_id,
        payload={
            "workflow_type": WorkflowType.KNOWLEDGE_COMPILE.value,
            "business_key": business_key,
            "display_name": "Compile governed Wiki draft",
            "input_refs": {
                "schema_version_id": str(body.schema_version_id),
                "prompt_version_id": str(body.prompt_version_id),
                "model_profile_id": str(body.model_profile_id),
            },
            "start_paused": False,
        },
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    job = await repository.create_compile_job(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="python"),
        workflow_task_id=UUID(str(task["id"])),
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    execution = await _gateway(request).start(
        workflow_name="nexweave.knowledge-compile.v2",
        workflow_id=str(task["workflow_id"]),
        payload={
            "workflow_type": WorkflowType.KNOWLEDGE_COMPILE.value,
            "task_id": str(task["id"]),
            "compile_job_id": str(job["id"]),
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
    job = await repository.mark_compile_started(
        compile_job_id=UUID(str(job["id"])),
        run_id=execution.run_id,
        actor_id=principal.actor_id,
    )
    return CompileJobResponse.model_validate(job)


@router.get("/spaces/{space_id}/compile-jobs", response_model=CompileJobListResponse)
async def list_compile_jobs(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> CompileJobListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="compile.read",
        trace_id=_trace_id(request),
    )
    return CompileJobListResponse.model_validate(
        {"items": await repository.list_compile_jobs(principal=principal, space_id=space_id)}
    )


@router.get("/compile-jobs/{compile_job_id}", response_model=CompileJobResponse)
async def get_compile_job(
    request: Request, compile_job_id: UUID, principal: PrincipalDependency
) -> CompileJobResponse:
    repository = _repository(request)
    job = await repository.get_compile_job(principal=principal, compile_job_id=compile_job_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(job["space_id"])),
        action="compile.read",
        trace_id=_trace_id(request),
    )
    return CompileJobResponse.model_validate(job)


@router.get("/spaces/{space_id}/entities", response_model=KnowledgeEntityListResponse)
async def list_entities(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> KnowledgeEntityListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="knowledge.read",
        trace_id=_trace_id(request),
    )
    return KnowledgeEntityListResponse.model_validate(
        {"items": await repository.list_entities(principal=principal, space_id=space_id)}
    )


@router.get("/spaces/{space_id}/wiki/pages", response_model=WikiPageListResponse)
async def list_wiki_pages(
    request: Request, space_id: UUID, principal: PrincipalDependency
) -> WikiPageListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="page.read",
        trace_id=_trace_id(request),
    )
    return WikiPageListResponse.model_validate(
        {"items": await repository.list_wiki_pages(principal=principal, space_id=space_id)}
    )


@router.get("/spaces/{space_id}/wiki-link-graph", response_model=WikiLinkGraphResponse)
async def get_wiki_link_graph(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    focus_page_id: UUID | None = None,
    max_depth: int = Query(default=2, ge=1, le=3),
    node_limit: int = Query(default=180, ge=10, le=500),
) -> WikiLinkGraphResponse:
    """Return a bounded Wiki navigation projection, never a Release graph."""
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="page.read",
        trace_id=_trace_id(request),
    )
    return WikiLinkGraphResponse.model_validate(
        await repository.get_wiki_link_graph(
            principal=principal,
            space_id=space_id,
            focus_page_id=focus_page_id,
            max_depth=max_depth,
            node_limit=node_limit,
        )
    )


@router.get("/wiki/pages/{page_id}", response_model=WikiPageResponse)
async def get_wiki_page(
    request: Request, page_id: UUID, principal: PrincipalDependency, response: Response
) -> WikiPageResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{page["version"]}"'
    return WikiPageResponse.model_validate(page)


@router.patch("/wiki/pages/{page_id}/drafts/{version_id}", response_model=WikiPageResponse)
async def edit_wiki_page(
    request: Request,
    page_id: UUID,
    version_id: UUID,
    body: WikiPageEdit,
    principal: PrincipalDependency,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    response: Response,
) -> WikiPageResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.edit",
        trace_id=_trace_id(request),
    )
    if UUID(str(page["current_version_id"])) != version_id:
        raise ApiProblem(
            409,
            "WIKI_VERSION_NOT_CURRENT",
            "Wiki version is not current",
            "Only the current draft can be edited; reload the page first.",
        )
    edited = await repository.edit_wiki_page(
        principal=principal,
        page_id=page_id,
        expected_version=_version_from_etag(if_match),
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{edited["version"]}"'
    return WikiPageResponse.model_validate(edited)


@router.get("/wiki/pages/{page_id}/versions", response_model=WikiPageVersionListResponse)
async def list_wiki_page_versions(
    request: Request, page_id: UUID, principal: PrincipalDependency
) -> WikiPageVersionListResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return WikiPageVersionListResponse.model_validate(
        {"items": await repository.list_wiki_page_versions(principal=principal, page_id=page_id)}
    )


@router.get("/wiki/pages/{page_id}/versions/{version_id}", response_model=WikiPageVersionResponse)
async def get_wiki_page_version(
    request: Request,
    page_id: UUID,
    version_id: UUID,
    principal: PrincipalDependency,
) -> WikiPageVersionResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return WikiPageVersionResponse.model_validate(
        await repository.get_wiki_page_version(
            principal=principal, page_id=page_id, version_id=version_id
        )
    )


@router.get("/wiki/pages/{page_id}/diff", response_model=WikiDiffResponse)
async def diff_wiki_page(
    request: Request,
    page_id: UUID,
    principal: PrincipalDependency,
    from_version_id: UUID,
    to_version_id: UUID,
) -> WikiDiffResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return WikiDiffResponse.model_validate(
        await repository.diff_wiki_page(
            principal=principal,
            page_id=page_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
        )
    )


@router.post(
    "/wiki/pages/{page_id}/comments",
    response_model=WikiCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_wiki_comment(
    request: Request,
    page_id: UUID,
    body: WikiCommentCreate,
    principal: PrincipalDependency,
) -> WikiCommentResponse:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.comment",
        trace_id=_trace_id(request),
    )
    return WikiCommentResponse.model_validate(
        await repository.add_wiki_comment(
            principal=principal, page_id=page_id, body=body.body, trace_id=_trace_id(request)
        )
    )


@router.put("/wiki/pages/{page_id}/follow")
async def follow_wiki_page(
    request: Request, page_id: UUID, principal: PrincipalDependency
) -> dict[str, object]:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return await repository.set_wiki_follow(principal=principal, page_id=page_id, follow=True)


@router.delete("/wiki/pages/{page_id}/follow")
async def unfollow_wiki_page(
    request: Request, page_id: UUID, principal: PrincipalDependency
) -> dict[str, object]:
    repository = _repository(request)
    page = await repository.get_wiki_page(principal=principal, page_id=page_id)
    await repository.authorize_space(
        principal=principal,
        space_id=UUID(str(page["space_id"])),
        action="page.read",
        trace_id=_trace_id(request),
    )
    return await repository.set_wiki_follow(principal=principal, page_id=page_id, follow=False)
