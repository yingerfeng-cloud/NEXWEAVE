"""Durable delivery reconciler; observes Temporal without duplicating its state machine."""

# ruff: noqa: E501 - adapter SQL
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text

from nexweave_api.forecast_execution import ForecastExecution
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.workflow_gateway import TemporalWorkflowGateway

LOGGER = logging.getLogger("nexweave.forecast.recovery")


class ForecastRecovery:
    def __init__(
        self,
        repository: ForecastRepository,
        gateway: TemporalWorkflowGateway,
        execution: ForecastExecution,
    ) -> None:
        self.repository, self.gateway, self.execution = repository, gateway, execution

    async def run(self) -> None:
        while True:
            try:
                await self.cycle()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.warning("Forecast reconciliation unavailable: %s", type(exc).__name__)
            await asyncio.sleep(self.repository.settings.forecast_reconcile_interval)

    async def cycle(self) -> None:
        # One reconciler across API processes. Transaction rollback releases the lock after a crash.
        async with self.repository.database.engine.begin() as lock:
            if not await lock.scalar(text("SELECT pg_try_advisory_xact_lock(953301)")):
                return
            rows = (
                (
                    await lock.execute(
                        text("""SELECT d.*,r.workflow_id,r.status AS run_status
                FROM forecast_delivery d JOIN forecast_runs r ON r.id=d.run_id
                WHERE d.next_attempt_at<=now() AND (d.cancel_pending OR d.status<>'TERMINAL')
                ORDER BY d.next_attempt_at,d.run_id LIMIT 50""")
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                try:
                    async with asyncio.timeout(10):
                        await self.reconcile(dict(row))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Safe code only; credentials, request arrays and raw RPC messages are not exposed.
                    code = "TEMPORAL_UNAVAILABLE" if not hasattr(exc, "code") else str(exc.code)
                    await self.update(
                        UUID(str(row["run_id"])),
                        "RETRYING",
                        code,
                        min(30, 2 ** min(int(row["attempts"]), 5)),
                    )

    async def update(
        self,
        run_id: UUID,
        status: str,
        error: str | None = None,
        delay: int = 5,
        *,
        clear_cancel: bool = False,
    ) -> None:
        async with self.repository.database.engine.begin() as c:
            await c.execute(
                text("""UPDATE forecast_delivery SET status=:status,error_code=CAST(:error AS varchar),
                attempts=attempts+CASE WHEN CAST(:error AS varchar) IS NOT NULL OR status='PENDING' THEN 1 ELSE 0 END,
                next_attempt_at=now()+(:delay * interval '1 second'),updated_at=now(),
                cancel_pending=CASE WHEN :clear THEN false ELSE cancel_pending END WHERE run_id=:id"""),
                {
                    "id": run_id,
                    "status": status,
                    "error": error,
                    "delay": delay,
                    "clear": clear_cancel,
                },
            )

    async def reconcile(self, row: dict[str, Any]) -> None:
        run_id = UUID(str(row["run_id"]))
        payload = {"workflow_type": "FORECAST", "run_id": str(run_id), "trace_id": row["trace_id"]}
        if row["run_status"] in {"SUCCEEDED", "FAILED", "CANCELLED"} and not row["cancel_pending"]:
            await self.update(run_id, "TERMINAL")
            return
        status = await self.gateway.forecast_status(row["workflow_id"])
        if row["cancel_pending"]:
            if status == "RUNNING":
                await self.gateway.cancel(workflow_id=row["workflow_id"])
            await self.update(run_id, "TERMINAL", clear_cancel=True)
            return
        if status is None and row["run_status"] == "QUEUED":
            await self.gateway.start(
                workflow_name=row["workflow_name"], workflow_id=row["workflow_id"], payload=payload
            )
            await self.update(run_id, "ACCEPTED")
            return
        if status == "RUNNING":
            await self.update(run_id, "ACCEPTED")
            return
        # Activity may have committed the immutable result before the workflow completed.
        run = await self.repository.raw_run(run_id)
        if run["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            await self.update(run_id, "TERMINAL")
            return
        if status == "CANCELED":
            await self.execution.fail(
                {**payload, "error_code": "WORKFLOW_CANCELLED", "terminal_status": "CANCELLED"}
            )
        else:
            code = {
                None: "WORKFLOW_HISTORY_MISSING",
                "COMPLETED": "WORKFLOW_RESULT_MISSING",
                "TIMED_OUT": "WORKFLOW_TIMED_OUT",
                "TERMINATED": "WORKFLOW_TERMINATED",
            }.get(status, "WORKFLOW_FAILED")
            await self.execution.fail({**payload, "error_code": code})
        await self.update(run_id, "TERMINAL")
