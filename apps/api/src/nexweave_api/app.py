from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any, cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp

from nexweave_api.database import Database
from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_execution import ForecastExecution
from nexweave_api.forecast_gateway import ForecastModelGateway
from nexweave_api.forecast_recovery import ForecastRecovery
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.forecast_routes import router as forecast_router
from nexweave_api.health import (
    DefaultInfrastructureProbe,
    InfrastructureProbe,
    ReadinessReport,
)
from nexweave_api.identity import LocalDevIdentityProvider, OidcIdentityProvider
from nexweave_api.integration_repository import IntegrationRepository
from nexweave_api.integration_routes import router as integration_router
from nexweave_api.knowledge_routes import router as knowledge_router
from nexweave_api.m1_routes import router as m1_router
from nexweave_api.object_storage import ClamAvInstreamMalwareScanner, S3ObjectStorage
from nexweave_api.release_routes import router as release_router
from nexweave_api.repository import PlatformRepository
from nexweave_api.review_routes import router as review_router
from nexweave_api.semantic_routes import router as semantic_router
from nexweave_api.settings import Settings, get_settings
from nexweave_api.source_routes import router as source_router
from nexweave_api.telemetry import configure_telemetry
from nexweave_api.trace_boundary import RequestTraceIsolation
from nexweave_api.workflow_gateway import TemporalWorkflowGateway
from nexweave_api.workflow_routes import router as workflow_router
from nexweave_contracts import ProblemDetails
from nexweave_contracts.runtime import IMPLEMENTATION_VERSION, MILESTONE, PHASE
from nexweave_domain import SemanticRuleViolation

LOGGER = logging.getLogger("nexweave.api")


def create_app(
    settings: Settings | None = None,
    infrastructure_probe: InfrastructureProbe | None = None,
    database: Database | None = None,
    repository: PlatformRepository | None = None,
    identity_provider: Any | None = None,
    object_storage: Any | None = None,
    malware_scanner: Any | None = None,
    workflow_gateway: Any | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    manage_runtime_services = infrastructure_probe is None
    probe = infrastructure_probe or DefaultInfrastructureProbe(resolved_settings)
    resolved_database = database or Database(resolved_settings)
    resolved_repository = repository or IntegrationRepository(resolved_database)
    resolved_identity_provider = identity_provider or (
        OidcIdentityProvider(resolved_settings)
        if resolved_settings.identity_provider == "oidc"
        else LocalDevIdentityProvider(resolved_settings)
    )
    resolved_object_storage = object_storage or S3ObjectStorage(resolved_settings)
    resolved_scanner = malware_scanner or ClamAvInstreamMalwareScanner(resolved_settings)
    resolved_workflow_gateway = workflow_gateway or TemporalWorkflowGateway(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if manage_runtime_services and resolved_settings.local_dev_identity_enabled:
            await resolved_repository.bootstrap_local_development(
                tenant_slug=resolved_settings.local_dev_tenant_slug,
                subject=resolved_settings.local_dev_subject,
            )
        if (
            manage_runtime_services
            and resolved_settings.object_store_access_key
            and resolved_settings.object_store_secret_key
        ):
            await resolved_object_storage.ensure_bucket()
        recovery_task = None
        if manage_runtime_services:
            forecast_repository = ForecastRepository(
                resolved_database,
                cast(IntegrationRepository, resolved_repository),
                resolved_settings,
            )
            recovery = ForecastRecovery(
                forecast_repository,
                resolved_workflow_gateway,
                ForecastExecution(
                    forecast_repository,
                    resolved_object_storage,
                    ForecastModelGateway(resolved_settings),
                ),
            )
            recovery_task = asyncio.create_task(recovery.run())
        try:
            yield
        finally:
            if recovery_task:
                recovery_task.cancel()
                with suppress(asyncio.CancelledError):
                    await recovery_task
            await resolved_workflow_gateway.close()
            await probe.close()
            await resolved_database.close()

    application = FastAPI(
        title="NEXWEAVE Platform API",
        version=IMPLEMENTATION_VERSION,
        description="R1 trusted knowledge with M9.5 Stage D trusted-read consolidation.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = resolved_database
    application.state.repository = resolved_repository
    application.state.identity_provider = resolved_identity_provider
    application.state.object_storage = resolved_object_storage
    application.state.malware_scanner = resolved_scanner
    application.state.workflow_gateway = resolved_workflow_gateway
    application.state.forecast_repository = ForecastRepository(
        resolved_database, cast(IntegrationRepository, resolved_repository), resolved_settings
    )
    application.include_router(forecast_router)
    application.include_router(m1_router)
    application.include_router(workflow_router)
    application.include_router(source_router)
    application.include_router(semantic_router)
    application.include_router(knowledge_router)
    application.include_router(review_router)
    application.include_router(release_router)
    application.include_router(integration_router)

    @application.middleware("http")
    async def trace_context(request: Request, call_next: Any) -> Response:
        span_context = trace.get_current_span().get_span_context()
        trace_id = (
            f"{span_context.trace_id:032x}"
            if span_context.is_valid
            else request.headers.get("X-Trace-Id", "")
        )
        if len(trace_id) != 32 or any(
            character not in "0123456789abcdef" for character in trace_id
        ):
            from secrets import token_hex

            trace_id = token_hex(16)
        request.state.trace_id = trace_id
        response: Response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(ApiProblem)
    async def api_problem(request: Request, exc: ApiProblem) -> JSONResponse:
        problem = ProblemDetails(
            type=f"https://docs.nexweave.local/problems/{exc.code.lower().replace('_', '-')}",
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            instance=str(request.url.path),
            code=exc.code,
            trace_id=getattr(request.state, "trace_id", None),
            extensions=exc.extensions,
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @application.exception_handler(SemanticRuleViolation)
    async def semantic_problem(request: Request, exc: SemanticRuleViolation) -> JSONResponse:
        status_code = 422
        if exc.code in {
            "PACK_DEPENDENCY_CONFLICT",
            "PACK_COMPOSITION_CONFLICT",
            "SEMANTIC_MAPPING_AMBIGUOUS",
            "SCHEMA_BREAKING_CHANGE",
        }:
            status_code = 409
        if exc.code in {"PACK_SIGNATURE_INVALID", "PACK_REVOKED"}:
            status_code = 403
        problem = ProblemDetails(
            type=f"https://docs.nexweave.local/problems/{exc.code.lower().replace('_', '-')}",
            title="Semantic model request rejected",
            status=status_code,
            detail=exc.detail,
            instance=str(request.url.path),
            code=exc.code,
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(
            status_code=status_code,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        problem = ProblemDetails(
            type="https://docs.nexweave.local/problems/validation-error",
            title="Request validation failed",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The request does not match the public contract.",
            instance=str(request.url.path),
            code="VALIDATION_ERROR",
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "VALIDATION_ERROR"
        problem = ProblemDetails(
            type=f"https://docs.nexweave.local/problems/{code.lower().replace('_', '-')}",
            title="Resource not found" if exc.status_code == 404 else "Request failed",
            status=exc.status_code,
            detail="The requested resource is unavailable."
            if exc.status_code == 404
            else "The request could not be completed.",
            instance=str(request.url.path),
            code=code,
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception(
            "Unhandled API error",
            extra={"trace_id": getattr(request.state, "trace_id", None)},
            exc_info=exc,
        )
        problem = ProblemDetails(
            type="https://docs.nexweave.local/problems/internal-error",
            title="Internal server error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The request could not be completed safely.",
            instance=str(request.url.path),
            code="INTERNAL_ERROR",
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @application.get("/api/v1/health/live", tags=["platform"])
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @application.get(
        "/api/v1/health/ready",
        tags=["platform"],
        response_model=ReadinessReport,
        responses={503: {"model": ReadinessReport, "description": "A required dependency is down"}},
    )
    async def readiness() -> JSONResponse:
        report = await probe.check()
        code = (
            status.HTTP_200_OK if report.status == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return JSONResponse(status_code=code, content=report.model_dump(mode="json"))

    @application.get("/api/v1/version", tags=["platform"])
    async def version() -> dict[str, str]:
        return {
            "product": "NEXWEAVE",
            "release": "R1",
            "milestone": MILESTONE,
            "phase": PHASE,
            "implementation_version": IMPLEMENTATION_VERSION,
            "build_version": resolved_settings.build_version,
        }

    @application.get("/api/v1/config/diagnostics", tags=["platform"])
    async def diagnostics() -> dict[str, dict[str, str]]:
        return {"configuration": resolved_settings.diagnostics()}

    configure_telemetry(application, resolved_database.engine, resolved_settings)
    original_build = application.build_middleware_stack

    def isolated_build() -> ASGIApp:
        return RequestTraceIsolation(original_build())

    # Outer ASGI boundary must run before the instrumentor's server-span middleware.
    application.build_middleware_stack = isolated_build  # type: ignore[method-assign]
    return application


app = create_app()
