from temporalio import workflow


@workflow.defn(name="nexweave.platform.health.v1")
class PlatformHealthWorkflow:
    """Deterministic M0 workflow; it performs no network, database, model or file I/O."""

    @workflow.run
    async def run(self) -> dict[str, str]:
        return {"status": "worker-ready", "milestone": "M0"}
