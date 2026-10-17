"""OIDC code + PKCE exchange with one-use, browser-bound login transactions."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import redis.asyncio as redis
from redis.exceptions import RedisError

from nexweave_api.errors import ApiProblem, AuthenticationFailed
from nexweave_api.identity import OidcIdentityProvider
from nexweave_api.m1_routes import _principal_response
from nexweave_api.repository import PlatformRepository
from nexweave_api.settings import Settings

COOKIE = "nxw_oidc_binding"
COOKIE_PATH = "/api/v1/auth/oidc"
TTL = 600


def append_query(url: str, values: dict[str, str]) -> str:
    parsed = urlsplit(url)
    return urlunsplit(parsed._replace(query=urlencode([*parse_qsl(parsed.query), *values.items()])))


class BrowserOidc:
    def __init__(
        self, settings: Settings, identity: OidcIdentityProvider, repository: PlatformRepository
    ):
        self.settings, self.identity, self.repository = settings, identity, repository
        self.store = redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
        self.token_transport: httpx.AsyncBaseTransport | None = None

    @property
    def callback(self) -> str:
        return self.settings.public_web_url.rstrip("/") + "/auth/callback"

    def require_enabled(self) -> None:
        if self.settings.identity_provider != "oidc" or not self.settings.oidc_web_enabled:
            raise ApiProblem(
                503,
                "OIDC_WEB_UNAVAILABLE",
                "OIDC Web unavailable",
                "Configure the trusted Web client before login.",
            )

    async def start(self) -> tuple[str, str]:
        self.require_enabled()
        state, binding, verifier, nonce = (secrets.token_urlsafe(32) for _ in range(4))
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        context = {
            "binding": hashlib.sha256(binding.encode()).hexdigest(),
            "verifier": verifier,
            "nonce": nonce,
        }
        try:
            await self.store.set(
                "nxw:oidc:" + hashlib.sha256(state.encode()).hexdigest(),
                json.dumps(context),
                ex=TTL,
                nx=True,
            )
        except RedisError as exc:
            raise ApiProblem(
                503,
                "OIDC_TRANSACTION_UNAVAILABLE",
                "Login unavailable",
                "Login transaction storage is unavailable.",
            ) from exc
        return append_query(
            self.settings.oidc_authorization_endpoint,
            {
                "response_type": "code",
                "client_id": self.settings.oidc_client_id,
                "redirect_uri": self.callback,
                "scope": "openid profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        ), binding

    async def exchange(self, *, code: str, state: str, binding: str, origin: str) -> dict[str, Any]:
        self.require_enabled()
        if origin != self.settings.public_web_url.rstrip("/") or not binding:
            raise AuthenticationFailed("The login response is not bound to this browser.")
        key = "nxw:oidc:" + hashlib.sha256(state.encode()).hexdigest()
        try:
            raw = await self.store.get(key)
            if not raw:
                raise AuthenticationFailed("The login transaction expired or was already used.")
            context = json.loads(raw)
            if not hmac.compare_digest(
                context["binding"], hashlib.sha256(binding.encode()).hexdigest()
            ):
                raise AuthenticationFailed("The login response is not bound to this browser.")
            # Matching the binding precedes atomic consumption so a foreign browser
            # cannot burn another user's legitimate transaction.
            if await self.store.getdel(key) != raw:
                raise AuthenticationFailed("The login transaction was already used.")
        except RedisError as exc:
            raise ApiProblem(
                503,
                "OIDC_TRANSACTION_UNAVAILABLE",
                "Login unavailable",
                "Login transaction storage is unavailable.",
            ) from exc
        secret = self.settings.oidc_client_secret.get_secret_value()
        try:
            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=False,
                trust_env=False,
                auth=httpx.BasicAuth(self.settings.oidc_client_id, secret) if secret else None,
                transport=self.token_transport,
            ) as client:
                response = await client.post(
                    self.settings.oidc_token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.settings.oidc_client_id,
                        "code": code,
                        "redirect_uri": self.callback,
                        "code_verifier": context["verifier"],
                    },
                )
                response.raise_for_status()
                tokens = response.json()
            if str(tokens.get("token_type", "")).lower() != "bearer":
                raise AuthenticationFailed("The identity provider did not return a Bearer session.")
            verified, expiry = await self.identity.verify_browser_tokens(
                id_token=tokens["id_token"],
                access_token=tokens["access_token"],
                nonce=context["nonce"],
                client_id=self.settings.oidc_client_id,
            )
            principal = await self.repository.resolve_principal(
                verified, issuer=self.settings.oidc_issuer
            )
            ttl = min(
                expiry - int(time.time()),
                self.settings.oidc_web_session_seconds,
                int(tokens.get("expires_in", 3600)),
            )
            if ttl <= 0:
                raise AuthenticationFailed("The returned login session has expired.")
            return {
                "access_token": tokens["access_token"],
                "token_type": "Bearer",
                "expires_in": ttl,
                "principal": _principal_response(principal).model_dump(mode="json"),
            }
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationFailed(
                "The identity provider could not complete login. Start a fresh login."
            ) from exc

    async def close(self) -> None:
        await self.store.aclose()
