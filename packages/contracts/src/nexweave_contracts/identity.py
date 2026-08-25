from datetime import datetime
from typing import Literal

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import ActorType, DataClassification, Role


class DevSessionRequest(ContractModel):
    subject: str = Field(min_length=1, max_length=255)


class PrincipalResponse(ContractModel):
    actor_type: ActorType
    actor_id: UUID7
    tenant_id: UUID7
    subject: str
    roles: tuple[Role, ...]
    clearance: DataClassification


class DevSessionResponse(ContractModel):
    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int = Field(gt=0)
    principal: PrincipalResponse


class OrganizationSummary(ContractModel):
    id: UUID7
    tenant_id: UUID7
    slug: str
    display_name: str
    status: str
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class OrganizationListResponse(ContractModel):
    items: tuple[OrganizationSummary, ...]
    next_cursor: str | None = None


class UserCreate(ContractModel):
    issuer: str = Field(min_length=1, max_length=512)
    subject: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    clearance: DataClassification = DataClassification.INTERNAL
    tenant_roles: tuple[Role, ...] = ()


class UserSummary(UserCreate):
    id: UUID7
    tenant_id: UUID7
    issuer: str
    subject: str
    display_name: str
    status: str
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class UserListResponse(ContractModel):
    items: tuple[UserSummary, ...]
    next_cursor: str | None = None


class ServiceIdentityCreate(ContractModel):
    client_id: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    clearance: DataClassification = DataClassification.INTERNAL
    audiences: tuple[str, ...] = Field(default=("nexweave-api",), min_length=1)
    credential_ref: str | None = Field(default=None, max_length=512)
    tenant_roles: tuple[Role, ...] = (Role.SERVICE,)

    @model_validator(mode="after")
    def enforce_least_privilege_service_policy(self) -> "ServiceIdentityCreate":
        if "nexweave-api" not in self.audiences:
            raise ValueError("service identities must include the nexweave-api audience")
        if set(self.tenant_roles) != {Role.SERVICE}:
            raise ValueError("service identities only receive the tenant-scoped service role")
        return self


class ServiceIdentitySummary(ServiceIdentityCreate):
    id: UUID7
    tenant_id: UUID7
    status: str
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class ServiceIdentityListResponse(ContractModel):
    items: tuple[ServiceIdentitySummary, ...]
    next_cursor: str | None = None


class RoleDescriptor(ContractModel):
    role: Role
    actions: tuple[str, ...]


class RoleListResponse(ContractModel):
    items: tuple[RoleDescriptor, ...]
    next_cursor: str | None = None
