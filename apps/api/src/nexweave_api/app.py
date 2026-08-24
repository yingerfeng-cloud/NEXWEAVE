from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nexweave_api.health import (
    DefaultInfrastructureProbe,
    InfrastructureProbe,
    ReadinessReport,
)
from nexweave_api.settings import Settings, get_settings
from nexweave_contracts import ProblemDetails
from nexweave_domain import new_uuid7


def create_app(
    settings: Settings | None = None,
    infrastructure_probe: InfrastructureProbe | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    probe = infrastructure_probe or DefaultInfrastructureProbe(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await probe.close()

    application = FastAPI(
        title="NEXWEAVE Platform API",
        version="1.0.0-m0",
        description="M0 platform health and diagnostics only; no knowledge business APIs.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def trace_context(request: Request, call_next: Any) -> Response:
        trace_id = str(new_uuid7())
        request.state.trace_id = trace_id
        response: Response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

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
            "milestone": "M0",
            "build_version": resolved_settings.build_version,
        }

    @application.get("/api/v1/config/diagnostics", tags=["platform"])
    async def diagnostics() -> dict[str, dict[str, str]]:
        return {"configuration": resolved_settings.diagnostics()}

    return application


app = create_app()
