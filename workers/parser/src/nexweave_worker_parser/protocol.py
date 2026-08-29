"""Credential-free parser capability and sandbox protocol vocabulary."""

from __future__ import annotations

from pathlib import PurePath

from nexweave_contracts import ParserCapability
from nexweave_domain import BlockType

PARSER_ID = "nexweave.parser.builtin"
PARSER_VERSION = "1.0.0"
DOCUMENT_MODEL_VERSION = "1.0"
LOCATOR_VERSION = "1.0"
SUPPORTED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class ParserPolicyError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def parser_capabilities() -> tuple[ParserCapability, ...]:
    return tuple(
        ParserCapability(
            provider_id=PARSER_ID,
            provider_version=PARSER_VERSION,
            mime_types=(mime,),
            block_types=tuple(BlockType),
            supports_scanned_pdf_detection=mime == "application/pdf",
            supports_ocr=False,
        )
        for mime in SUPPORTED_TYPES
    )


def probe_type(*, filename: str, content_type: str, content: bytes) -> ParserCapability:
    suffix = PurePath(filename).suffix.lower()
    expected = SUPPORTED_TYPES.get(content_type)
    if expected is None or suffix != expected:
        raise ParserPolicyError(
            "SOURCE_TYPE_UNSUPPORTED", "The extension and declared MIME are not an approved pair."
        )
    if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise ParserPolicyError("SOURCE_TYPE_UNSUPPORTED", "The PDF magic bytes do not match.")
    if content_type.endswith(
        ("wordprocessingml.document", "spreadsheetml.sheet")
    ) and not content.startswith(b"PK\x03\x04"):
        raise ParserPolicyError("SOURCE_TYPE_UNSUPPORTED", "The OOXML magic bytes do not match.")
    if b"\x00" in content[:4096] and content_type.startswith("text/"):
        raise ParserPolicyError("SOURCE_TYPE_UNSUPPORTED", "The text file contains binary bytes.")
    return next(item for item in parser_capabilities() if content_type in item.mime_types)
