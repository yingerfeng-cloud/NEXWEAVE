"""Local-development and production OIDC identity-provider adapters."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient

from nexweave_api.errors import AuthenticationFailed
from nexweave_api.settings import Settings
from nexweave_domain import ActorType, DataClassification, Principal


def _audience_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise AuthenticationFailed("The token audience claim is invalid.")


def _principal_from_claims(claims: dict[str, Any]) -> Principal:
    try:
        return Principal(
            actor_type=ActorType(str(claims["nexweave_actor_type"])),
            actor_id=UUID(str(claims["nexweave_actor_id"])),
            tenant_id=UUID(str(claims["nexweave_tenant_id"])),
            subject=str(claims["sub"]),
            audience=_audience_tuple(claims["aud"]),
            tenant_roles=frozenset(),
            clearance=DataClassification(str(claims.get("nexweave_clearance", "INTERNAL"))),
            token_id=str(claims["jti"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationFailed("The token identity claims are incomplete.") from exc


class LocalDevIdentityProvider:
    issuer = "https://identity.nexweave.local/dev"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.local_dev_signing_key
        self._audience = settings.oidc_audience
        self._session_seconds = settings.local_dev_session_seconds

    def issue(self, principal: Principal) -> tuple[str, int]:
        now = datetime.now(UTC)
        claims = {
            "iss": self.issuer,
            "sub": principal.subject,
            "aud": self._audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=self._session_seconds),
            "jti": principal.token_id,
            "nexweave_actor_type": principal.actor_type.value,
            "nexweave_actor_id": str(principal.actor_id),
            "nexweave_tenant_id": str(principal.tenant_id),
            "nexweave_clearance": principal.clearance.value,
        }
        return jwt.encode(claims, self._key, algorithm="HS256"), self._session_seconds

    async def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "sub", "aud", "jti"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed(
                "The local development token is invalid or expired."
            ) from exc
        return _principal_from_claims(claims)


class OidcIdentityProvider:
    """Verify asymmetric OIDC access tokens without binding to a particular IAM vendor."""

    def __init__(self, settings: Settings) -> None:
        self._issuer = settings.oidc_issuer
        self._audience = settings.oidc_audience
        self._algorithms = [item.strip() for item in settings.oidc_algorithms.split(",")]
        self._jwks = PyJWKClient(settings.oidc_jwks_url, cache_keys=True)

    async def verify(self, token: str) -> Principal:
        try:
            signing_key = await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud", "jti"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("The OIDC token is invalid or expired.") from exc
        return _principal_from_claims(claims)
