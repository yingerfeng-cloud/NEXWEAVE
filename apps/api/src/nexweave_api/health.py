from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal, Protocol
from urllib.parse import urlsplit

import httpx
import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from nexweave_api.settings import Settings


class ComponentHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["up", "down"]
    detail: str | None = None


class ReadinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "not_ready"]
    components: dict[str, ComponentHealth]


class InfrastructureProbe(Protocol):
    async def check(self) -> ReadinessReport: ...

    async def close(self) -> None: ...


class DefaultInfrastructureProbe:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
        )

    async def check(self) -> ReadinessReport:
        checks: dict[str, Callable[[], Awaitable[None]]] = {
            "postgresql": self._check_postgresql,
            "redis": self._check_redis,
            "object_storage": self._check_object_storage,
            "temporal": self._check_temporal,
        }
        results = await asyncio.gather(*(self._run_check(check) for check in checks.values()))
        components = dict(zip(checks, results, strict=True))
        status: Literal["ready", "not_ready"] = (
            "ready" if all(item.status == "up" for item in components.values()) else "not_ready"
        )
        return ReadinessReport(status=status, components=components)

    async def close(self) -> None:
        await self._engine.dispose()

    async def _run_check(self, check: Callable[[], Awaitable[None]]) -> ComponentHealth:
        try:
            await asyncio.wait_for(check(), timeout=self._settings.health_timeout_seconds)
        except Exception as exc:
            return ComponentHealth(status="down", detail=type(exc).__name__)
        return ComponentHealth(status="up")

    async def _check_postgresql(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def _check_redis(self) -> None:
        client = redis.from_url(  # type: ignore[no-untyped-call]
            self._settings.redis_url, socket_timeout=2
        )
        try:
            response = await client.ping()
            if response is not True:
                raise RuntimeError("Redis ping returned an unexpected response")
        finally:
            await client.aclose()

    async def _check_object_storage(self) -> None:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(self._settings.object_store_health_url)
            response.raise_for_status()

    async def _check_temporal(self) -> None:
        host, port = _split_host_port(self._settings.temporal_endpoint)
        reader, writer = await asyncio.open_connection(host, port)
        del reader
        writer.close()
        await writer.wait_closed()


def _split_host_port(endpoint: str) -> tuple[str, int]:
    parsed = urlsplit(endpoint if "://" in endpoint else f"tcp://{endpoint}")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("Temporal endpoint must include host and port")
    return parsed.hostname, parsed.port
