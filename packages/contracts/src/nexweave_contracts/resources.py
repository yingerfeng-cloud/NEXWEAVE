from datetime import datetime

from pydantic import UUID7, Field, field_validator

from nexweave_contracts.base import ContractModel


class ResourceMetadata(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7 | None = None
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value
