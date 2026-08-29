"""Credential-free, network-isolated parser sandbox server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
from typing import Any

from pydantic import ValidationError

from nexweave_contracts import ParseRequest
from nexweave_worker_parser.parsers import DocumentParserRegistry
from nexweave_worker_parser.protocol import ParserPolicyError

LOGGER = logging.getLogger("nexweave.parser.sandbox")
MAX_HEADER_BYTES = 65_536
MAX_INPUT_BYTES = 536_870_912


async def _send(writer: asyncio.StreamWriter, value: dict[str, Any]) -> None:
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    writer.write(struct.pack("!I", len(encoded)))
    writer.write(encoded)
    await writer.drain()


async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        header_size = struct.unpack("!I", await reader.readexactly(4))[0]
        if header_size > MAX_HEADER_BYTES:
            raise ParserPolicyError(
                "PARSER_RESOURCE_LIMIT_EXCEEDED", "The parser request header is too large."
            )
        request = ParseRequest.model_validate_json(await reader.readexactly(header_size))
        content_size = struct.unpack("!Q", await reader.readexactly(8))[0]
        if (
            content_size > MAX_INPUT_BYTES
            or content_size > request.budget.max_input_bytes
            or content_size != request.source.size
        ):
            raise ParserPolicyError(
                "PARSER_RESOURCE_LIMIT_EXCEEDED",
                "The parser input does not satisfy its immutable size budget.",
            )
        content = await reader.readexactly(content_size)
        async with asyncio.timeout(request.budget.timeout_seconds):
            manifest = await DocumentParserRegistry().parse(request=request, content=content)
        await _send(writer, {"ok": True, "manifest": manifest.model_dump(mode="json")})
    except ParserPolicyError as exc:
        await _send(writer, {"ok": False, "code": exc.code, "detail": exc.detail})
    except TimeoutError:
        await _send(
            writer,
            {
                "ok": False,
                "code": "PARSER_RESOURCE_LIMIT_EXCEEDED",
                "detail": "The parser exceeded its sandbox wall-clock budget.",
            },
        )
    except (ValidationError, json.JSONDecodeError, struct.error) as exc:
        await _send(
            writer,
            {
                "ok": False,
                "code": "PARSE_RESULT_INVALID",
                "detail": f"The parser request failed validation ({type(exc).__name__}).",
            },
        )
    except asyncio.IncompleteReadError:
        pass
    except Exception as exc:
        LOGGER.exception("parser sandbox failed", extra={"error_type": type(exc).__name__})
        await _send(
            writer,
            {
                "ok": False,
                "code": "PARSE_RESULT_INVALID",
                "detail": f"The parser sandbox failed safely ({type(exc).__name__}).",
            },
        )
    finally:
        writer.close()
        await writer.wait_closed()


async def run() -> None:
    host = os.environ.get("NEXWEAVE_PARSER_SANDBOX_BIND", "0.0.0.0")  # noqa: S104
    port = int(os.environ.get("NEXWEAVE_PARSER_SANDBOX_PORT", "7001"))
    logging.basicConfig(level=os.environ.get("NEXWEAVE_LOG_LEVEL", "INFO"))
    server = await asyncio.start_server(_handle, host, port, limit=MAX_INPUT_BYTES + 1)
    LOGGER.info("credential-free parser sandbox ready", extra={"port": port})
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(run())
