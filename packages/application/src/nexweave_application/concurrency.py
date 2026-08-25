"""Stable request hashing and HTTP optimistic-lock helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


def _canonical_value(value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical request timestamps must include a timezone")
        return value.isoformat()
    raise TypeError(f"unsupported canonical request value: {type(value).__name__}")


def canonical_request_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_value,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def etag_for_version(version: int) -> str:
    if version < 1:
        raise ValueError("version must be positive")
    return f'"v{version}"'
