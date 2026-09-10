"""Stage A request isolation and durable delivery decisions."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from opentelemetry import context, trace

from nexweave_api.app import create_app
from nexweave_api.forecast_recovery import ForecastRecovery
from nexweave_api.health import ReadinessReport
from nexweave_api.settings import Settings


class Probe:
    async def check(self):
        return ReadinessReport(status="ready", components={})

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_concurrent_requests_ignore_inherited_span_and_restore_caller_context():
    app = create_app(Settings(_env_file=None), Probe())
    inherited = trace.NonRecordingSpan(
        trace.SpanContext(
            trace_id=int("a" * 32, 16),
            span_id=123,
            is_remote=False,
            trace_flags=trace.TraceFlags(1),
        )
    )
    token = context.attach(trace.set_span_in_context(inherited))
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            ids = [uuid4().hex for _ in range(12)]
            responses = await asyncio.gather(
                *[
                    client.get(
                        "/api/v1/version", headers={"traceparent": f"00-{i}-0123456789abcdef-01"}
                    )
                    for i in ids
                ]
            )
            assert [r.headers["x-trace-id"] for r in responses] == ids
            malformed = await client.get("/api/v1/version", headers={"traceparent": "invalid"})
            absent = await client.get("/api/v1/version")
            assert malformed.headers["x-trace-id"] != "a" * 32
            assert absent.headers["x-trace-id"] != malformed.headers["x-trace-id"]
            assert trace.get_current_span() is inherited
    finally:
        context.detach(token)


def recovery(status, run_status="QUEUED", cancel=False):
    repo = SimpleNamespace(raw_run=AsyncMock(return_value={"status": run_status}))
    gateway = SimpleNamespace(
        forecast_status=AsyncMock(return_value=status), start=AsyncMock(), cancel=AsyncMock()
    )
    execution = SimpleNamespace(fail=AsyncMock())
    service = ForecastRecovery(repo, gateway, execution)
    service.update = AsyncMock()
    row = {
        "run_id": str(uuid4()),
        "run_status": run_status,
        "cancel_pending": cancel,
        "trace_id": "a" * 32,
        "workflow_id": "fixed-id",
        "workflow_name": "nexweave.forecast.v2",
    }
    return service, row


@pytest.mark.asyncio
async def test_pending_delivery_uses_same_workflow_identity_then_does_not_restart():
    service, row = recovery(None)
    await service.reconcile(row)
    assert service.gateway.start.call_args.kwargs["workflow_id"] == "fixed-id"
    assert set(service.gateway.start.call_args.kwargs["payload"]) == {
        "workflow_type",
        "run_id",
        "trace_id",
    }
    service.gateway.forecast_status.return_value = "RUNNING"
    await service.reconcile(row)
    assert service.gateway.start.await_count == 1


@pytest.mark.asyncio
async def test_failed_delivery_is_not_marked_accepted():
    service, row = recovery(None)
    service.gateway.start.side_effect = RuntimeError("transport")
    with pytest.raises(RuntimeError):
        await service.reconcile(row)
    service.update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("temporal", [None, "RUNNING", "COMPLETED"])
async def test_cancelled_database_run_never_starts_or_publishes(temporal):
    service, row = recovery(temporal, "CANCELLED", True)
    await service.reconcile(row)
    service.gateway.start.assert_not_awaited()
    assert service.gateway.cancel.await_count == (1 if temporal == "RUNNING" else 0)
    service.execution.fail.assert_not_awaited()
    assert service.update.call_args.kwargs["clear_cancel"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temporal,code",
    [
        (None, "WORKFLOW_HISTORY_MISSING"),
        ("COMPLETED", "WORKFLOW_RESULT_MISSING"),
        ("TIMED_OUT", "WORKFLOW_TIMED_OUT"),
    ],
)
async def test_missing_result_reconciles_to_explicit_failure(temporal, code):
    service, row = recovery(temporal, "RUNNING")
    await service.reconcile(row)
    assert service.execution.fail.call_args.args[0]["error_code"] == code


@pytest.mark.asyncio
async def test_committed_artifact_wins_over_workflow_failure():
    service, row = recovery("FAILED", "RUNNING")
    service.repository.raw_run.return_value = {"status": "SUCCEEDED"}
    await service.reconcile(row)
    service.execution.fail.assert_not_awaited()
