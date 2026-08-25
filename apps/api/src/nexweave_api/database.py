"""PostgreSQL connection lifecycle for API adapters."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from nexweave_api.settings import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )

    async def close(self) -> None:
        await self.engine.dispose()
