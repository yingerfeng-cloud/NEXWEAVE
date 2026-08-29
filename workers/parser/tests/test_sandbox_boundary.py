import asyncio
import hashlib

import pytest

from nexweave_contracts import ControlledObjectRef, ParseRequest
from nexweave_domain import ParseJobStatus, new_uuid7
from nexweave_worker_parser.sandbox_client import SandboxParserClient
from nexweave_worker_parser.sandbox_server import _handle


@pytest.mark.integration
async def test_credential_free_sandbox_protocol_round_trip() -> None:
    content = b"Sandboxed parser content."
    checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
    tenant, space, source, version, job = (new_uuid7() for _ in range(5))
    request = ParseRequest(
        parse_job_id=job,
        source=ControlledObjectRef(
            source_version_id=version,
            object_key=f"raw/v1/{tenant}/{space}/{source}/{version}/{checksum.removeprefix('sha256:')}",
            object_version_id="immutable-v1",
            checksum_sha256=checksum,
            content_type="text/plain",
            size=len(content),
        ),
        filename="sandbox.txt",
        parser_id="nexweave.parser.builtin",
        parser_version="1.0.0",
        config_checksum="sha256:" + "d" * 64,
    )
    server = await asyncio.start_server(_handle, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        result = await SandboxParserClient("127.0.0.1", port).parse(
            request=request, content=content
        )
    finally:
        server.close()
        await server.wait_closed()

    assert result.status is ParseJobStatus.SUCCEEDED
    assert result.source_version_id == version
