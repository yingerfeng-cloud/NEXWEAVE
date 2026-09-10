"""Provider-neutral numerical inference and time-series input ports."""

from typing import Any, Protocol

from nexweave_contracts.forecast import TimeSeriesCapabilities


class TimeSeriesModelProvider(Protocol):
    def capabilities(self) -> TimeSeriesCapabilities: ...

    async def forecast(self, context: dict[str, Any]) -> dict[str, Any]: ...


class TimeSeriesConnector(Protocol):
    async def read_window(self, *, object_key: str, checksum: str) -> bytes: ...
