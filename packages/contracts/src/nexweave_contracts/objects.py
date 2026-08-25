from datetime import datetime

from pydantic import UUID7, Field

from nexweave_contracts.base import ContractModel
from nexweave_domain import DataClassification, ScanStatus, UploadSessionStatus


class ObjectUploadCreate(ContractModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=255)
    expected_size: int = Field(gt=0, le=104_857_600)
    classification: DataClassification = DataClassification.INTERNAL


class ObjectUploadSessionResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    filename: str
    content_type: str
    expected_size: int
    classification: DataClassification
    status: UploadSessionStatus
    version: int = Field(ge=1)
    upload_url: str
    expires_at: datetime
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ManagedObjectResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    filename: str
    object_key: str
    object_version_id: str | None = None
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_type: str
    size: int = Field(gt=0)
    classification: DataClassification
    scan_status: ScanStatus
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ObjectDownloadResponse(ContractModel):
    url: str
    expires_at: datetime
