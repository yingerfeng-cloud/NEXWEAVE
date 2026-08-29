from typing import Annotated, Literal

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import LocatorStatus


class PageLocator(ContractModel):
    kind: Literal["page"] = "page"
    page: int = Field(ge=1)


class BlockLocator(ContractModel):
    kind: Literal["block"] = "block"
    block_id: str = Field(min_length=1, max_length=512)


class CharacterRangeLocator(ContractModel):
    kind: Literal["character_range"] = "character_range"
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text_basis: Literal["normalized_utf8", "source_utf8"]

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "CharacterRangeLocator":
        if self.end <= self.start:
            raise ValueError("character range end must be greater than start")
        return self


class TableCellLocator(ContractModel):
    kind: Literal["table_cell"] = "table_cell"
    table_id: str = Field(min_length=1, max_length=512)
    row_start: int = Field(ge=0)
    row_end: int = Field(ge=0)
    column_start: int = Field(ge=0)
    column_end: int = Field(ge=0)


class BoundingBoxLocator(ContractModel):
    kind: Literal["bounding_box"] = "bounding_box"
    page: int = Field(ge=1)
    coordinate_system: Literal["normalized_top_left"] = "normalized_top_left"
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def box_must_fit_normalized_page(self) -> "BoundingBoxLocator":
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("bounding box must fit inside normalized page")
        return self


class TimeRangeLocator(ContractModel):
    kind: Literal["time_range"] = "time_range"
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "TimeRangeLocator":
        if self.end_ms <= self.start_ms:
            raise ValueError("time range end must be greater than start")
        return self


Locator = Annotated[
    PageLocator
    | BlockLocator
    | CharacterRangeLocator
    | TableCellLocator
    | BoundingBoxLocator
    | TimeRangeLocator,
    Field(discriminator="kind"),
]


class SourceAnchor(ContractModel):
    id: UUID7
    source_version_id: UUID7
    parse_job_id: UUID7 | None = None
    locator_version: Literal["1.0"] = "1.0"
    source_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    excerpt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    locators: tuple[Locator, ...] = Field(min_length=1)
    status: LocatorStatus
    relocated_from_anchor_id: UUID7 | None = None
