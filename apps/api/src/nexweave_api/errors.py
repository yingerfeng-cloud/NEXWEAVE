"""Stable application-to-HTTP problem mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiProblem(Exception):
    status: int
    code: str
    title: str
    detail: str
    extensions: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.detail


class AuthenticationFailed(ApiProblem):
    def __init__(self, detail: str = "A valid bearer token is required.") -> None:
        super().__init__(401, "AUTHENTICATION_REQUIRED", "Authentication required", detail)
