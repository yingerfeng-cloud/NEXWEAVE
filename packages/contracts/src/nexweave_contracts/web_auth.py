"""Web login bootstrap; resource APIs continue to use verified Bearer tokens."""

from typing import Literal

from pydantic import Field

from nexweave_contracts.base import ContractModel
from nexweave_contracts.identity import DevSessionResponse


class WebAuthConfig(ContractModel):
    provider: Literal["local", "oidc"]
    login_enabled: bool
    issuer: str | None = None
    login_url: str | None = None
    logout_url: str | None = None


class OidcCodeExchange(ContractModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class WebSessionResponse(DevSessionResponse):
    """Short-lived user access token from the configured external identity provider."""
