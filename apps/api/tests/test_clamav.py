import struct
from typing import Any

import pytest

from nexweave_api.errors import ApiProblem
from nexweave_api.object_storage import ClamAvInstreamMalwareScanner
from nexweave_api.settings import Settings
from nexweave_domain import ScanStatus


class ReaderStub:
    def __init__(self, response: bytes) -> None:
        self.response = response

    async def readuntil(self, separator: bytes) -> bytes:
        assert separator == b"\0"
        return self.response


class WriterStub:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None


@pytest.mark.asyncio
async def test_clamav_adapter_uses_bounded_instream_protocol(monkeypatch: Any) -> None:
    writer = WriterStub()

    async def connect(host: str, port: int):  # type: ignore[no-untyped-def]
        assert host == "clamav" and port == 3310
        return ReaderStub(b"stream: OK\0"), writer

    monkeypatch.setattr("asyncio.open_connection", connect)
    scanner = ClamAvInstreamMalwareScanner(
        Settings(_env_file=None, clamav_host="clamav", clamav_port=3310)
    )

    result = await scanner.scan(content=b"synthetic", content_type="text/plain")

    assert result is ScanStatus.CLEAN
    assert writer.writes == [
        b"zINSTREAM\0",
        struct.pack("!I", len(b"synthetic")),
        b"synthetic",
        struct.pack("!I", 0),
    ]


@pytest.mark.asyncio
async def test_clamav_ambiguous_response_fails_closed(monkeypatch: Any) -> None:
    writer = WriterStub()

    async def connect(host: str, port: int):  # type: ignore[no-untyped-def]
        del host, port
        return ReaderStub(b"stream: UNKNOWN\0"), writer

    monkeypatch.setattr("asyncio.open_connection", connect)
    scanner = ClamAvInstreamMalwareScanner(Settings(_env_file=None))

    with pytest.raises(ApiProblem) as error:
        await scanner.scan(content=b"synthetic", content_type="text/plain")

    assert error.value.code == "SOURCE_MALWARE_SCAN_FAILED"
    assert error.value.extensions["retryable"] is False
