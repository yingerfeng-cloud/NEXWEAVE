from typing import Any

from pydantic import Field

from nexweave_contracts.base import ContractModel


class FieldError(ContractModel):
    pointer: str = Field(pattern=r"^(/.*)?$")
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    message: str


class ProblemDetails(ContractModel):
    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str | None = None
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    trace_id: str | None = None
    errors: tuple[FieldError, ...] = ()
    extensions: dict[str, Any] = Field(default_factory=dict)
