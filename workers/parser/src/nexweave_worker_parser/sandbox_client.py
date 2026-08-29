"""Trusted coordinator client for the credential-free parser sandbox."""

from __future__ import annotations

import asyncio
import json
import struct

from nexweave_contracts import ParserCapability, ParseRequest, ParseResultManifest
from nexweave_worker_parser.protocol import (
    ParserPolicyError,
    parser_capabilities,
    probe_type,
)

MAX_RESPONSE_BYTES = 268_435_456


class SandboxParserClient:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def capabilities(self) -> tuple[ParserCapability, ...]:
        return parser_capabilities()

    def probe(self, *, filename: str, content_type: str, content: bytes) -> ParserCapability:
        return probe_type(filename=filename, content_type=content_type, content=content)

    async def parse(self, *, request: ParseRequest, content: bytes) -> ParseResultManifest:
        reader, writer = await asyncio.open_connection(self._host, self._port)
        try:
            header = request.model_dump_json().encode("utf-8")
            writer.write(struct.pack("!I", len(header)))
            writer.write(header)
            writer.write(struct.pack("!Q", len(content)))
            writer.write(content)
            await writer.drain()
            response_size = struct.unpack("!I", await reader.readexactly(4))[0]
            if response_size > MAX_RESPONSE_BYTES:
                raise ParserPolicyError(
                    "PARSER_RESOURCE_LIMIT_EXCEEDED",
                    "The parser sandbox response exceeded its transport budget.",
                )
            payload = json.loads((await reader.readexactly(response_size)).decode("utf-8"))
            if not payload.get("ok"):
                raise ParserPolicyError(
                    str(payload.get("code") or "PARSE_RESULT_INVALID"),
                    str(payload.get("detail") or "The parser sandbox rejected the input."),
                )
            return ParseResultManifest.model_validate(payload["manifest"])
        except (OSError, asyncio.IncompleteReadError) as exc:
            raise ParserPolicyError(
                "PARSER_DEPENDENCY_UNAVAILABLE",
                "The credential-free parser sandbox is unavailable.",
            ) from exc
        finally:
            writer.close()
            await writer.wait_closed()
