from datetime import datetime
from typing import Any

from pydantic import UUID7, Field, field_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import DataClassification


class EventEnvelope(ContractModel):
    specversion: str = Field(default="1.0", pattern=r"^1\.0$")
    id: UUID7
    type: str = Field(pattern=r"^io\.nexweave\.[a-z0-9_.]+\.v[1-9][0-9]*$")
    source: str = Field(pattern=r"^/nexweave/[a-z0-9/_-]+$")
    subject: str
    time: datetime
    datacontenttype: str = "application/json"
    dataschema: str
    tenant_id: UUID7
    space_id: UUID7 | None = None
    aggregate_id: UUID7
    aggregate_version: int = Field(ge=1)
    correlation_id: UUID7
    causation_id: UUID7 | None = None
    trace_id: str | None = None
    classification: DataClassification
    data: dict[str, Any]

    @field_validator("time")
    @classmethod
    def time_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event time must include a timezone")
        return value
