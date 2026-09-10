"""Deterministic M9.5 workflow. Payload/history contain identifiers, never input arrays."""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError


@workflow.defn(name="nexweave.forecast.v1")
class ForecastWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result: dict[str, Any] = await workflow.execute_activity(
                "nexweave.forecast.execute",
                payload,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return result
        except ActivityError as exc:
            cause = exc.cause
            code = getattr(cause, "type", None) or "FORECAST_EXECUTION_FAILED"
            await workflow.execute_activity(
                "nexweave.forecast.fail",
                {**payload, "error_code": code},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise
