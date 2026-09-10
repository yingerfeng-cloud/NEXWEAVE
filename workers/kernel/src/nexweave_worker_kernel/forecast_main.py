"""Isolated optional CPU worker; importing the API never loads Torch."""

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from sqlalchemy import text
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from nexweave_api.database import Database
from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_execution import ForecastExecution
from nexweave_api.forecast_gateway import Chronos2Provider, ForecastModelGateway
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.integration_repository import IntegrationRepository
from nexweave_api.object_storage import S3ObjectStorage
from nexweave_api.settings import Settings
from nexweave_contracts.runtime import IMPLEMENTATION_VERSION
from nexweave_domain import SemanticRuleViolation, new_uuid7
from nexweave_worker_kernel.forecast_workflow import ForecastWorkflow
from nexweave_worker_kernel.forecast_workflow_v2 import ForecastWorkflowV2


async def main(on_ready: Callable[[], None] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    await asyncio.to_thread(Chronos2Provider(settings).verify_model)
    database = Database(settings)
    worker_id = new_uuid7()

    async def lease() -> None:
        while True:
            async with database.engine.begin() as c:
                await c.execute(
                    text(
                        "INSERT INTO forecast_worker_leases"
                        "(id,queue,implementation_version,model_revision,ready) "
                        "VALUES(:id,:queue,:version,:revision,true) "
                        "ON CONFLICT(id) DO UPDATE SET seen_at=now(),ready=true"
                    ),
                    {
                        "id": worker_id,
                        "queue": settings.forecast_task_queue,
                        "version": IMPLEMENTATION_VERSION,
                        "revision": settings.forecast_model_revision,
                    },
                )
            if on_ready:
                on_ready()
            await asyncio.sleep(5)

    service = ForecastExecution(
        ForecastRepository(database, IntegrationRepository(database), settings),
        S3ObjectStorage(settings),
        ForecastModelGateway(settings),
    )

    @activity.defn(name="nexweave.forecast.execute")
    async def execute(payload: dict[str, Any]) -> dict[str, Any]:
        async def heartbeat() -> None:
            while True:
                activity.heartbeat()
                await asyncio.sleep(3)

        pulse = asyncio.create_task(heartbeat())
        try:
            return await service.execute(payload)
        except (SemanticRuleViolation, ApiProblem) as exc:
            raise ApplicationError(
                "Forecast request could not be executed.",
                type=exc.code,
                non_retryable=isinstance(exc, SemanticRuleViolation) or exc.status < 500,
            ) from exc
        finally:
            pulse.cancel()
            with suppress(asyncio.CancelledError):
                await pulse

    @activity.defn(name="nexweave.forecast.fail")
    async def fail(payload: dict[str, Any]) -> None:
        await service.fail(payload)

    try:
        client = await Client.connect(
            settings.temporal_endpoint, namespace=settings.temporal_namespace
        )
        async with Worker(
            client,
            task_queue=settings.forecast_task_queue,
            workflows=[ForecastWorkflow, ForecastWorkflowV2],
            activities=[execute, fail],
            max_concurrent_activities=1,
        ):
            await lease()
    finally:
        try:
            async with database.engine.begin() as c:
                await c.execute(
                    text(
                        "UPDATE forecast_worker_leases SET ready=false,seen_at=now() WHERE id=:id"
                    ),
                    {"id": worker_id},
                )
        finally:
            await database.close()


if __name__ == "__main__":
    asyncio.run(main())
