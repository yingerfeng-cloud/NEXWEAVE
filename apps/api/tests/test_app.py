from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from nexweave_api.app import create_app
from nexweave_api.errors import ApiProblem
from nexweave_api.health import ComponentHealth, ReadinessReport
from nexweave_api.m1_routes import _paginate
from nexweave_api.settings import Settings
from nexweave_api.workflow_gateway import _merge_temporal_state


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
    application = create_app(Settings(_env_file=None), probe)
    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_platform_endpoints_report_m2_without_exposing_later_business_routes() -> None:
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
    assert version.json()["milestone"] == "M2"
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


@pytest.mark.asyncio
async def test_authenticated_routes_default_to_denied_and_return_traceable_problem_details() -> (
    None
):
    report = ReadinessReport(status="ready", components={})
    async with client_for(StubProbe(report)) as client:
        response = await client.get("/api/v1/spaces")

    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.json()["trace_id"] == response.headers["x-trace-id"]


@pytest.mark.asyncio
async def test_w3c_trace_context_is_returned_by_the_api() -> None:
    trace_id = "0123456789abcdef0123456789abcdef"
    traceparent = f"00-{trace_id}-0123456789abcdef-01"
    report = ReadinessReport(status="ready", components={})
    async with client_for(StubProbe(report)) as client:
        response = await client.get("/api/v1/version", headers={"traceparent": traceparent})

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == trace_id


def test_stable_cursor_pagination_continues_after_the_last_item() -> None:
    items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    first = _paginate(items, 2, None)
    second = _paginate(items, 2, first["next_cursor"])

    assert first["items"] == items[:2]
    assert second == {"items": items[2:], "next_cursor": None}


def test_stable_cursor_pagination_rejects_an_unknown_anchor() -> None:
    with pytest.raises(ApiProblem, match="anchor is unavailable") as error:
        _paginate([{"id": "a"}], 1, "dW5rbm93bg")

    assert error.value.status == 400
    assert error.value.code == "INVALID_CURSOR"


def test_closed_temporal_status_overrides_stale_workflow_query_snapshot() -> None:
    state = _merge_temporal_state(
        {"status": "PAUSED", "run_id": "old-run"}, "authoritative-run", "TERMINATED"
    )

    assert state["status"] == "FAILED"
    assert state["run_id"] == "authoritative-run"
    assert state["temporal_status"] == "TERMINATED"
