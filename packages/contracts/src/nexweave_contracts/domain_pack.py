"""Canonical, non-executable M4 Domain Pack public contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from nexweave_contracts.base import ContractModel

PACK_ID = r"^[a-z][a-z0-9-]{1,62}-pack$"
KEY_NAMESPACE = r"^[a-z][a-z0-9.-]{1,62}$"
PACK_PATH = r"^[a-z0-9][a-z0-9._/-]{0,191}$"
SHA256 = r"^sha256:[0-9a-f]{64}$"
SEMVER = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"


class DomainPackMetadata(ContractModel):
    id: str = Field(pattern=PACK_ID)
    version: str = Field(pattern=SEMVER)
    publisher: str = Field(min_length=1, max_length=255)
    keyNamespace: str = Field(pattern=KEY_NAMESPACE)
    description: str = Field(max_length=4000)


class DomainPackDependency(ContractModel):
    id: str = Field(pattern=PACK_ID)
    versionRange: str = Field(min_length=1, max_length=128)


class DomainPackCompatibility(ContractModel):
    platform: str = Field(min_length=1, max_length=128)
    semanticContract: str = Field(min_length=1, max_length=128)
    dependencies: tuple[DomainPackDependency, ...] = Field(default=(), max_length=32)


class DomainPackContentEntry(ContractModel):
    path: str = Field(pattern=PACK_PATH)
    sha256: str = Field(pattern=SHA256)


class DomainPackSignature(ContractModel):
    algorithm: Literal["Ed25519"]
    keyId: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}$")
    value: str = Field(pattern=r"^[A-Za-z0-9_-]{86}$")


class DomainPackSecurity(ContractModel):
    executableContent: Literal[False]
    signature: DomainPackSignature


class DomainPackManifestV1Alpha1(ContractModel):
    apiVersion: Literal["nexweave.io/domain-pack/v1alpha1"]
    kind: Literal["NexweaveDomainPack"]
    canonicalizationAlgorithm: Literal["RFC8785-JCS/1"]
    metadata: DomainPackMetadata
    compatibility: DomainPackCompatibility
    content: dict[str, DomainPackContentEntry] = Field(min_length=1, max_length=64)
    security: DomainPackSecurity


class DomainPackRevocationEntry(ContractModel):
    keyId: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{1,128}$")
    packId: str | None = Field(default=None, pattern=PACK_ID)
    version: str | None = Field(default=None, pattern=SEMVER)
    contentChecksum: str | None = Field(default=None, pattern=SHA256)
    reasonCode: str = Field(pattern=r"^[A-Z0-9_]{1,128}$")
    revokedAt: datetime


class DomainPackRevocationListV1Alpha1(ContractModel):
    apiVersion: Literal["nexweave.io/pack-revocation/v1alpha1"]
    kind: Literal["NexweavePackRevocationList"]
    canonicalizationAlgorithm: Literal["RFC8785-JCS/1"]
    revoked: tuple[DomainPackRevocationEntry, ...] = Field(min_length=1, max_length=1000)
    security: DomainPackSecurity
