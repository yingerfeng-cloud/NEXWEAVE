"""Minimal, versioned M4 Schema and Pack event payloads."""

from typing import Literal

from pydantic import UUID7, Field

from nexweave_contracts.base import ContractModel


class SchemaPackReference(ContractModel):
    domain_pack_version_id: UUID7
    content_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SchemaPublishedEventData(ContractModel):
    schema_definition_id: UUID7
    schema_version_id: UUID7
    semantic_version: str = Field(min_length=1, max_length=64)
    composition_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pack_inputs: tuple[SchemaPackReference, ...] = Field(default=(), max_length=32)


class PackInstalledEventData(ContractModel):
    installation_id: UUID7
    domain_pack_version_id: UUID7
    candidate_schema_version_id: UUID7
    composition_checksum: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    operation: Literal["INSTALL", "UPGRADE", "DISABLE", "ROLLBACK"]
