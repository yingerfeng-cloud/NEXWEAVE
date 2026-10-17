"""Durable, retryable delivery of committed review facts to Temporal."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text

from nexweave_api.errors import ApiProblem
from nexweave_api.review_repository import ReviewRepository
from nexweave_api.workflow_gateway import TemporalWorkflowGateway


class ReviewDelivery:
    def __init__(self, repository: ReviewRepository, gateway: TemporalWorkflowGateway):
        self.repository, self.gateway = repository, gateway

    async def deliver(self, case_id: UUID | None = None, *, tenant_id: UUID | None = None) -> None:
        async with self.repository._database.engine.begin() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT d.*,wt.workflow_id,rc.workflow_task_id "
                            "FROM review_deliveries d "
                            "JOIN review_cases rc ON rc.id=d.review_case_id "
                            "JOIN workflow_tasks wt ON wt.id=rc.workflow_task_id "
                            "WHERE d.delivered_at IS NULL "
                            "AND d.next_attempt_at<=now() "
                            "AND (CAST(:tenant AS uuid) IS NULL OR rc.tenant_id=:tenant) "
                            "AND (CAST(:case AS uuid) IS NULL OR d.review_case_id=:case) "
                            "ORDER BY d.created_at,d.kind DESC LIMIT 25 FOR UPDATE OF d SKIP LOCKED"
                        ),
                        {"case": case_id, "tenant": tenant_id},
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                payload = dict(row["payload"])
                try:
                    if row["kind"] == "START":
                        execution = await asyncio.wait_for(
                            self.gateway.start(
                                workflow_name="nexweave.human-review.v2",
                                workflow_id=row["workflow_id"],
                                payload=payload,
                            ),
                            timeout=5,
                        )
                        await self.repository.mark_workflow_started(
                            task_id=row["workflow_task_id"],
                            run_id=execution.run_id,
                            actor_id=UUID(payload["actor_id"]),
                            trace_id=payload["trace_id"],
                        )
                    else:
                        expected = {
                            "review_case_id": str(row["review_case_id"]),
                            "status": "APPROVED" if payload["action"] == "APPROVE" else "REJECTED",
                        }
                        completed = await asyncio.wait_for(
                            self.gateway.completed_review_result(row["workflow_id"]), timeout=5
                        )
                        if completed is not None and completed != expected:
                            raise ApiProblem(
                                409,
                                "REVIEW_WORKFLOW_RESULT_MISMATCH",
                                "Review pending",
                                "Workflow result does not match the audited final decision.",
                            )
                        if completed is None:
                            state = await asyncio.wait_for(
                                self.gateway.inspect(workflow_id=row["workflow_id"]), timeout=5
                            )
                            if (
                                state.get("status") != "WAITING"
                                or state.get("current_step") != "wait-for-audited-final-decision"
                            ):
                                raise ApiProblem(
                                    503,
                                    "REVIEW_WORKFLOW_NOT_READY",
                                    "Review pending",
                                    "The workflow is not ready for its audited decision.",
                                )
                        try:
                            if completed is None:
                                await asyncio.wait_for(
                                    self.gateway.command(
                                        workflow_id=row["workflow_id"],
                                        command_id=f"review-delivery:{row['id']}:attempt:{row['attempts']}",
                                        action=payload["action"],
                                        reason=payload["reason"],
                                        actor_id=payload["actor_id"],
                                    ),
                                    timeout=5,
                                )
                        except ApiProblem:
                            # A crash after Temporal accepted the update but before
                            # this transaction committed must not poison recovery.
                            result = await asyncio.wait_for(
                                self.gateway.completed_review_result(row["workflow_id"]), timeout=5
                            )
                            if result != expected:
                                raise
                    await connection.execute(
                        text(
                            "UPDATE review_deliveries SET delivered_at=:now,attempts=attempts+1,"
                            "last_error=NULL WHERE id=:id"
                        ),
                        {"now": datetime.now(UTC), "id": row["id"]},
                    )
                except Exception as exc:
                    await connection.execute(
                        text(
                            "UPDATE review_deliveries SET attempts=attempts+1,"
                            "last_error=:error,next_attempt_at=:next WHERE id=:id"
                        ),
                        {
                            "id": row["id"],
                            "error": (
                                exc.code[:64]
                                if isinstance(exc, ApiProblem)
                                else "WORKFLOW_DELIVERY_TIMEOUT"
                                if isinstance(exc, TimeoutError)
                                else "REVIEW_DELIVERY_FAILED"
                            ),
                            "next": datetime.now(UTC)
                            + timedelta(seconds=min(60, 2 ** min(int(row["attempts"]) + 1, 6))),
                        },
                    )
                    # One failed review must not starve other tenants/cases.
                    continue

    async def run(self) -> None:
        while True:
            try:
                await self.deliver()
                await self.reconcile_completed()
            except Exception:
                # Database/network outages leave durable records pending. Never log
                # review text, credentials or raw provider exceptions.
                import logging

                logging.getLogger(__name__).warning("Review delivery reconciliation deferred")
            await asyncio.sleep(2)

    async def reconcile_completed(self) -> None:
        """Repair pre-fix or crash-window projections only from a matching real result."""
        async with self.repository._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT d.review_case_id,d.payload,rc.workflow_task_id,wt.workflow_id "
                            "FROM review_deliveries d "
                            "JOIN review_cases rc ON rc.id=d.review_case_id "
                            "JOIN workflow_tasks wt ON wt.id=rc.workflow_task_id "
                            "WHERE d.kind='DECISION' AND d.delivered_at IS NOT NULL "
                            "AND wt.status NOT IN "
                            "('SUCCEEDED','FAILED','REJECTED','CANCELLED','TIMED_OUT') "
                            "ORDER BY d.created_at LIMIT 10"
                        )
                    )
                )
                .mappings()
                .all()
            )
        for row in rows:
            result = await asyncio.wait_for(
                self.gateway.completed_review_result(row["workflow_id"]), timeout=5
            )
            expected = "APPROVED" if row["payload"]["action"] == "APPROVE" else "REJECTED"
            if result != {"review_case_id": str(row["review_case_id"]), "status": expected}:
                continue
            actual = await asyncio.wait_for(
                self.gateway.inspect(workflow_id=row["workflow_id"]), timeout=5
            )
            await self.repository.apply_projection_event(
                {
                    "task_id": str(row["workflow_task_id"]),
                    "actor_id": row["payload"]["actor_id"],
                    "run_id": actual["run_id"],
                    "trace_id": "",
                    "event_type": "REVIEW_TERMINAL_RECONCILED",
                    "event_key": f"review-delivery:{row['review_case_id']}:"
                    f"{actual['run_id']}:terminal",
                    "status": "SUCCEEDED" if expected == "APPROVED" else "REJECTED",
                    "progress": 100,
                    "step_key": "wait-for-audited-final-decision",
                    "result_summary": result,
                    "message": "Projection reconciled from matching Temporal review result",
                    "details": {"authority": "Temporal", "automatic_delivery_reconciliation": True},
                }
            )
