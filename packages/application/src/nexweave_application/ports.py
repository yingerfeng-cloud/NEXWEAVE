"""Provider-neutral application ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from nexweave_domain import Principal, ScanStatus

if TYPE_CHECKING:
    from nexweave_contracts import (
        ControlledObjectRef,
        ParserCapability,
        ParseRequest,
        ParseResultManifest,
    )


@dataclass(frozen=True, slots=True)
class StoredObjectInfo:
    key: str
    version_id: str | None
    size: int
    checksum_sha256: str
    content_type: str


class IdentityProviderPort(Protocol):
    async def verify(self, token: str) -> Principal: ...


class ObjectStoragePort(Protocol):
    async def ensure_bucket(self) -> None: ...

    async def put_if_absent(
        self, *, key: str, content: bytes, content_type: str, checksum_sha256: str
    ) -> StoredObjectInfo: ...

    async def create_download_url(self, *, key: str, expires_seconds: int) -> str: ...

    async def get(self, *, key: str, version_id: str | None = None) -> bytes: ...

    async def head(self, *, key: str, version_id: str | None = None) -> StoredObjectInfo: ...


class MalwareScannerPort(Protocol):
    async def scan(self, *, content: bytes, content_type: str) -> ScanStatus: ...


@dataclass(frozen=True, slots=True)
class OcrRegion:
    page: int
    image_object: ControlledObjectRef
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0


@dataclass(frozen=True, slots=True)
class OcrText:
    text: str
    page: int
    x: float
    y: float
    width: float
    height: float
    confidence: float
    provider_id: str
    provider_version: str
    config_checksum: str


class ParserPort(Protocol):
    def capabilities(self) -> tuple[ParserCapability, ...]: ...

    def probe(self, *, filename: str, content_type: str, content: bytes) -> ParserCapability: ...

    async def parse(self, *, request: ParseRequest, content: bytes) -> ParseResultManifest: ...


class OcrPort(Protocol):
    def capabilities(self) -> tuple[str, ...]: ...

    async def recognize(
        self, *, region: OcrRegion, config_checksum: str
    ) -> tuple[OcrText, ...]: ...


@dataclass(frozen=True, slots=True)
class WorkflowExecutionInfo:
    workflow_id: str
    run_id: str
    temporal_status: str


class WorkflowGatewayPort(Protocol):
    async def start(
        self, *, workflow_name: str, workflow_id: str, payload: dict[str, Any]
    ) -> WorkflowExecutionInfo: ...

    async def command(
        self, *, workflow_id: str, command_id: str, action: str, reason: str, actor_id: str
    ) -> dict[str, Any]: ...

    async def retry(
        self, *, workflow_name: str, workflow_id: str, payload: dict[str, Any]
    ) -> WorkflowExecutionInfo: ...

    async def cancel(self, *, workflow_id: str) -> None: ...

    async def inspect(self, *, workflow_id: str) -> dict[str, Any]: ...
