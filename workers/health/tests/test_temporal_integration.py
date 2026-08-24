import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nexweave_worker_health.workflows import PlatformHealthWorkflow


async def _execute_health_workflow() -> dict[str, str]:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        task_queue = "nexweave-m0-integration"
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[PlatformHealthWorkflow],
        ):
            return await environment.client.execute_workflow(
                PlatformHealthWorkflow.run,
                id="nexweave-m0-health-integration",
                task_queue=task_queue,
            )


@pytest.mark.integration
async def test_health_workflow_runs_on_real_temporal_test_server() -> None:
    result = await _execute_health_workflow()
    assert result == {"status": "worker-ready", "milestone": "M0"}
