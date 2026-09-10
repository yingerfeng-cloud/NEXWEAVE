"""M4 SchemaVersion and declarative Pack API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import UUID7, Field, SerializerFunctionWrapHandler, model_serializer

from nexweave_contracts.base import ContractModel
from nexweave_contracts.forecast import ForecastProfile, SignalDefinition
from nexweave_contracts.resources import ResourceMetadata

STABLE_KEY_PATTERN = r"^[a-z][a-z0-9.-]{1,62}/[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
StableKey = str
Checksum = str


class EntityTypeDeclaration(ContractModel):
    key: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    displayName: str = Field(min_length=1, max_length=255)
    abstract: bool = False


class PropertyDeclaration(ContractModel):
    key: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    typeKey: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    dataType: Literal["STRING", "INTEGER", "BOOLEAN", "DATE", "DATETIME", "DECIMAL", "REFERENCE"]
    required: bool = False
    minCount: int = Field(default=0, ge=0)
    maxCount: int | None = Field(default=1, ge=1)
    enum: tuple[str, ...] = Field(default=(), max_length=256)
    referenceTypeKey: StableKey | None = None
    default: str | int | bool | None = None
    unique: bool = False
    mergeStrategy: Literal["REPLACE", "APPEND", "SET_UNION", "MANUAL"] = "MANUAL"


class TypeHierarchyDeclaration(ContractModel):
    child: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    parent: StableKey = Field(pattern=STABLE_KEY_PATTERN)


class RelationTypeDeclaration(ContractModel):
    key: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    domain: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    range: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    direction: Literal["DIRECTED", "UNDIRECTED"] = "DIRECTED"
    minCount: int = Field(default=0, ge=0)
    maxCount: int | None = Field(default=None, ge=1)
    inverseOf: StableKey | None = None
    causal: bool = False
    temporal: bool = False
    evidenceRequired: bool = False


class TypeTermDeclaration(ContractModel):
    targetKey: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    language: str = Field(min_length=2, max_length=35)
    term: str = Field(min_length=1, max_length=512)
    kind: Literal["PREFERRED", "ALIAS", "ABBREVIATION"]
    scope: str = Field(default="GLOBAL", min_length=1, max_length=128)


class ConceptMappingDeclaration(ContractModel):
    source: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    target: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    kind: Literal["EXACT", "BROADER", "NARROWER", "RELATED"]
    provenance: str = Field(min_length=1, max_length=512)
    reviewStatus: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING"


class KeyedDeclaration(ContractModel):
    key: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    definition: dict[str, Any] = Field(default_factory=dict)


class SemanticDeclarations(ContractModel):
    signalDefinitions: tuple[SignalDefinition, ...] = Field(default=(), max_length=1000)
    forecastProfiles: tuple[ForecastProfile, ...] = Field(default=(), max_length=100)

    @model_serializer(mode="wrap")
    def preserve_legacy_snapshot(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        for key in ("signalDefinitions", "forecastProfiles"):
            if not result.get(key):
                result.pop(key, None)
        return result

    types: tuple[EntityTypeDeclaration, ...] = Field(default=(), max_length=10_000)
    properties: tuple[PropertyDeclaration, ...] = Field(default=(), max_length=50_000)
    hierarchy: tuple[TypeHierarchyDeclaration, ...] = Field(default=(), max_length=50_000)
    relations: tuple[RelationTypeDeclaration, ...] = Field(default=(), max_length=50_000)
    terms: tuple[TypeTermDeclaration, ...] = Field(default=(), max_length=50_000)
    mappings: tuple[ConceptMappingDeclaration, ...] = Field(default=(), max_length=50_000)
    templates: tuple[KeyedDeclaration, ...] = Field(default=(), max_length=1_000)
    lintRules: tuple[KeyedDeclaration, ...] = Field(default=(), max_length=1_000)
    evaluationSuites: tuple[KeyedDeclaration, ...] = Field(default=(), max_length=1_000)
    ui: tuple[KeyedDeclaration, ...] = Field(default=(), max_length=1_000)


class SchemaCreate(ContractModel):
    schema_key: StableKey = Field(pattern=STABLE_KEY_PATTERN)
    display_name: str = Field(min_length=1, max_length=255)
    semantic_version: str = Field(default="0.1.0", min_length=1, max_length=64)
    snapshot: SemanticDeclarations = Field(default_factory=SemanticDeclarations)


class SchemaVersionCreate(ContractModel):
    semantic_version: str = Field(min_length=1, max_length=64)
    snapshot: SemanticDeclarations


class SchemaComposeRequest(ContractModel):
    semantic_version: str = Field(min_length=1, max_length=64)
    domain_pack_version_ids: tuple[UUID7, ...] = Field(min_length=1, max_length=32)
    local_declarations: SemanticDeclarations = Field(default_factory=SemanticDeclarations)


class SchemaVersionResponse(ResourceMetadata):
    schema_definition_id: UUID7
    schema_key: StableKey
    semantic_version: str
    status: Literal["DRAFT", "TESTING", "PUBLISHED", "DEPRECATED"]
    content_checksum: Checksum
    composition_checksum: Checksum
    canonicalization_algorithm: str
    breaking_change: bool
    normalized_snapshot: dict[str, Any]


class SchemaListResponse(ContractModel):
    items: tuple[SchemaVersionResponse, ...]


class CompositionReportResponse(ResourceMetadata):
    schema_version_id: UUID7
    input_checksum: Checksum
    result_checksum: Checksum
    report: dict[str, Any]


class DomainPackInstallationCreate(ContractModel):
    domain_pack_version_id: UUID7
    schema_definition_id: UUID7
    semantic_version: str = Field(min_length=1, max_length=64)
    operation: Literal["INSTALL", "UPGRADE"] = "INSTALL"
    previous_installation_id: UUID7 | None = None


class DomainPackInstallationResponse(ResourceMetadata):
    domain_pack_version_id: UUID7
    schema_definition_id: UUID7
    requested_semantic_version: str
    operation: Literal["INSTALL", "UPGRADE", "DISABLE", "ROLLBACK"]
    previous_installation_id: UUID7 | None
    workflow_task_id: UUID7 | None
    workflow_id: str
    run_id: str | None
    candidate_schema_version_id: UUID7 | None
    composition_report_id: UUID7 | None
    status: Literal[
        "PLANNED", "INSTALLING", "ACTIVE", "FAILED", "ROLLING_BACK", "ROLLED_BACK", "DISABLED"
    ]


class DomainPackRollbackCreate(ContractModel):
    target_installation_id: UUID7


class DomainPackTrustKeyCreate(ContractModel):
    key_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}$")
    key_namespace: str = Field(pattern=r"^[a-z][a-z0-9.-]{1,62}$")
    public_key_base64url: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    valid_from: datetime
    valid_until: datetime | None = None


class DomainPackRegisterRequest(ContractModel):
    manifest: dict[str, Any]
    contents: dict[str, dict[str, Any]] = Field(min_length=1, max_length=64)


class DomainPackVersionResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    pack_key: str = Field(pattern=r"^[a-z][a-z0-9-]{0,62}-pack$")
    pack_version: str
    publisher: str
    key_namespace: str = Field(pattern=r"^[a-z][a-z0-9.-]{1,62}$")
    content_checksum: Checksum
    signature_key_id: str
    status: Literal["VALIDATED", "PUBLISHED"]
    created_at: datetime


class DomainPackVersionListResponse(ContractModel):
    items: tuple[DomainPackVersionResponse, ...]


class DomainPackTrustKeyResponse(ResourceMetadata):
    key_id: str
    key_namespace: str
    algorithm: Literal["Ed25519"]
    fingerprint: Checksum
    status: Literal["ACTIVE", "REVOKED", "EXPIRED", "DISABLED"]
    valid_from: datetime
    valid_until: datetime | None


class DomainPackRevocationImportResponse(ContractModel):
    evidence_checksum: Checksum
    signing_key_id: str
    revocation_ids: tuple[UUID7, ...]
