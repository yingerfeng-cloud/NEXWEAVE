"""Stable identifier helpers."""

from __future__ import annotations

import secrets
import time
from uuid import UUID

MAX_UUID7_TIMESTAMP_MS = (1 << 48) - 1


def new_uuid7(now_ms: int | None = None) -> UUID:
    """Generate an RFC 9562 UUIDv7 using a millisecond timestamp and secure randomness."""
    timestamp_ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    if not 0 <= timestamp_ms <= MAX_UUID7_TIMESTAMP_MS:
        raise ValueError("UUIDv7 timestamp must fit in 48 unsigned bits")

    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return UUID(int=value)
