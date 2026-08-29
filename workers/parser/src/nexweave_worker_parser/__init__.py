"""M3 parser adapters with lazy loading across the sandbox boundary."""

from typing import TYPE_CHECKING, Any

from nexweave_worker_parser.protocol import ParserPolicyError

if TYPE_CHECKING:
    from nexweave_worker_parser.parsers import DocumentParserRegistry

__all__ = ["DocumentParserRegistry", "ParserPolicyError"]


def __getattr__(name: str) -> Any:
    if name == "DocumentParserRegistry":
        from nexweave_worker_parser.parsers import DocumentParserRegistry

        return DocumentParserRegistry
    raise AttributeError(name)
