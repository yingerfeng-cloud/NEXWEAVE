from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from nexweave_api.app import create_app
from nexweave_api.health import ComponentHealth, ReadinessReport
from nexweave_api.settings import Settings


class StubProbe:
    def __init__(self, report: ReadinessReport) -> None:
        self.report = report
        self.closed = False

    async def check(self) -> ReadinessReport:
        return self.report

    async def close(self) -> None:
        self.closed = True


@asynccontextmanager
async def client_for(probe: StubProbe) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(Settings(), probe)
    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_platform_endpoints_do_not_expose_business_routes_or_secrets() -> None:
    report = ReadinessReport(
        status="ready",
        components={"postgresql": ComponentHealth(status="up")},
    )
    probe = StubProbe(report)
    async with client_for(probe) as client:
        live = await client.get("/api/v1/health/live")
        ready = await client.get("/api/v1/health/ready")
        version = await client.get("/api/v1/version")
        diagnostics = await client.get("/api/v1/config/diagnostics")
        missing_business_route = await client.get("/api/v1/sources")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert version.json()["milestone"] == "M0"
    assert "local@" not in str(diagnostics.json())
    assert missing_business_route.status_code == 404
    assert probe.closed is True


@pytest.mark.asyncio
async def test_readiness_is_unavailable_when_a_dependency_is_down() -> None:
    report = ReadinessReport(
        status="not_ready",
        components={"temporal": ComponentHealth(status="down", detail="TimeoutError")},
    )
    async with client_for(StubProbe(report)) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["components"]["temporal"]["detail"] == "TimeoutError"
