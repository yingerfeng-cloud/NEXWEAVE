"""OIDC protocol/component checks with real RSA verification and substitute IdP/store.

These tests are not external IAM or browser acceptance. PostgreSQL issuer binding
and actual Redis transactions are exercised separately by integration tests.
"""

import asyncio
import base64
import hashlib
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from nexweave_api.errors import AuthenticationFailed
from nexweave_api.identity import OidcIdentityProvider
from nexweave_api.settings import Settings
from nexweave_api.web_auth import BrowserOidc
from nexweave_domain import ActorType, DataClassification, Principal, new_uuid7


class MemoryTransactions:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, **kwargs):
        assert kwargs == {"ex": 600, "nx": True}
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def getdel(self, key):
        return self.values.pop(key, None)


@pytest.fixture
def login_components():
    settings = Settings(
        _env_file=None,
        identity_provider="oidc",
        oidc_issuer="https://iam.example.test",
        oidc_jwks_url="https://iam.example.test/keys",
        oidc_web_enabled=True,
        oidc_authorization_endpoint="https://iam.example.test/authorize",
        oidc_token_endpoint="https://iam.example.test/token",  # noqa: S106 - synthetic URL, not a secret
        oidc_client_id="nxw-web",
        public_web_url="https://portal.example.test",
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider = OidcIdentityProvider(settings)
    provider._jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())
    )
    actor = Principal(
        actor_type=ActorType.USER,
        actor_id=new_uuid7(),
        tenant_id=new_uuid7(),
        subject="business-role",
        audience=("nexweave-api",),
        tenant_roles=frozenset(),
        clearance=DataClassification.INTERNAL,
        token_id=str(new_uuid7()),
    )
    repository = SimpleNamespace(resolve_principal=AsyncMock(return_value=actor))
    service = BrowserOidc(settings, provider, repository)
    service.store = MemoryTransactions()

    def tokens(context, changes=None):
        now = int(time.time())
        access_claims = {
            "iss": settings.oidc_issuer,
            "sub": actor.subject,
            "aud": "nexweave-api",
            "iat": now,
            "exp": now + 900,
            "jti": actor.token_id,
            "nexweave_actor_type": "USER",
            "nexweave_actor_id": str(actor.actor_id),
            "nexweave_tenant_id": str(actor.tenant_id),
        }
        access = jwt.encode(access_claims, key, algorithm="RS256")
        digest = hashlib.sha256(access.encode()).digest()
        claims = {
            "iss": settings.oidc_issuer,
            "sub": actor.subject,
            "aud": settings.oidc_client_id,
            "iat": now,
            "exp": now + 600,
            "nonce": context["nonce"],
            "at_hash": base64.urlsafe_b64encode(digest[:16]).decode().rstrip("="),
            **(changes or {}),
        }
        return {
            "token_type": "Bearer",
            "expires_in": 900,
            "access_token": access,
            "id_token": jwt.encode(claims, key, algorithm="RS256"),
        }

    return SimpleNamespace(
        service=service,
        settings=settings,
        repository=repository,
        actor=actor,
        tokens=tokens,
        key=key,
    )


@pytest.mark.asyncio
async def test_browser_bound_pkce_exchange_and_replay(login_components):
    s = login_components
    url, binding = await s.service.start()
    query = parse_qs(urlsplit(url).query)
    context = json.loads(next(iter(s.service.store.values.values())))
    assert query["response_type"] == ["code"] and query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == ["https://portal.example.test/auth/callback"]

    def token_endpoint(request):
        form = parse_qs(request.content.decode())
        assert request.url == s.settings.oidc_token_endpoint
        assert form["code_verifier"] == [context["verifier"]]
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"][0].encode()).digest())
            .decode()
            .rstrip("=")
        )
        assert query["code_challenge"] == [challenge]
        return httpx.Response(200, json=s.tokens(context))

    s.service.token_transport = httpx.MockTransport(token_endpoint)
    inputs = {
        "code": "one-use-code",
        "state": query["state"][0],
        "origin": s.settings.public_web_url,
    }
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(**inputs, binding="different-browser")
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(
            **{**inputs, "origin": "https://foreign.example.test"}, binding=binding
        )
    result = await s.service.exchange(**inputs, binding=binding)
    assert result["principal"]["actor_id"] == str(s.actor.actor_id)
    assert 0 < result["expires_in"] <= 600
    s.repository.resolve_principal.assert_awaited_once_with(s.actor, issuer=s.settings.oidc_issuer)
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(**inputs, binding=binding)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"nonce": "wrong"},
        {"aud": "other-client"},
        {"azp": "other-client"},
        {"aud": ["nxw-web", "other-client"]},
        {"sub": "different-user"},
        {"at_hash": "wrong"},
        {"exp": 1},
        {"iss": "https://foreign.example.test"},
    ],
)
async def test_oidc_invalid_login_tokens_are_rejected(login_components, changes):
    s = login_components
    url, binding = await s.service.start()
    context = json.loads(next(iter(s.service.store.values.values())))
    s.service.token_transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json=s.tokens(context, changes))
    )
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(
            code="one-use-code",
            state=parse_qs(urlsplit(url).query)["state"][0],
            binding=binding,
            origin=s.settings.public_web_url,
        )
    s.repository.resolve_principal.assert_not_awaited()


@pytest.mark.asyncio
async def test_oidc_simultaneous_callback_consumes_state_once(login_components):
    s = login_components
    url, binding = await s.service.start()
    context = json.loads(next(iter(s.service.store.values.values())))
    s.service.token_transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json=s.tokens(context))
    )
    inputs = {
        "code": "same-code",
        "state": parse_qs(urlsplit(url).query)["state"][0],
        "binding": binding,
        "origin": s.settings.public_web_url,
    }
    results = await asyncio.gather(
        s.service.exchange(**inputs), s.service.exchange(**inputs), return_exceptions=True
    )
    assert len([r for r in results if isinstance(r, dict)]) == 1
    assert len([r for r in results if isinstance(r, AuthenticationFailed)]) == 1


@pytest.mark.asyncio
async def test_oidc_rejects_tampered_signature_and_expired_state(login_components):
    s = login_components
    url, binding = await s.service.start()
    context = json.loads(next(iter(s.service.store.values.values())))
    tokens = s.tokens(context)
    tokens["id_token"] = tokens["id_token"].rsplit(".", 1)[0] + ".bm90LWEtdmFsaWQtc2lnbmF0dXJl"
    s.service.token_transport = httpx.MockTransport(lambda _: httpx.Response(200, json=tokens))
    inputs = {
        "code": "same-code",
        "state": parse_qs(urlsplit(url).query)["state"][0],
        "binding": binding,
        "origin": s.settings.public_web_url,
    }
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(**inputs)
    s.repository.resolve_principal.assert_not_awaited()
    s.service.store.values.clear()
    with pytest.raises(AuthenticationFailed):
        await s.service.exchange(**inputs)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oidc_real_redis_and_actual_routes_with_substitute_iam(login_components):
    import redis.asyncio as redis

    from nexweave_api.app import create_app

    url = os.environ.get("NEXWEAVE_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set NEXWEAVE_TEST_REDIS_URL to an isolated Redis instance")
    s = login_components
    s.service.store = redis.from_url(url, decode_responses=True)
    app = create_app(s.settings, repository=s.repository, identity_provider=s.service.identity)
    unused = app.state.browser_oidc
    app.state.browser_oidc = s.service

    def token_endpoint(request):
        form = parse_qs(request.content.decode())
        assert form["code_verifier"] == [context["verifier"]]
        return httpx.Response(200, json=s.tokens(context))

    s.service.token_transport = httpx.MockTransport(token_endpoint)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=s.settings.public_web_url
        ) as client:
            started = await client.get("/api/v1/auth/oidc/login", follow_redirects=False)
            assert started.status_code == 302
            assert (
                "HttpOnly" in started.headers["set-cookie"]
                and "Secure" in started.headers["set-cookie"]
            )
            state = parse_qs(urlsplit(started.headers["location"]).query)["state"][0]
            key = "nxw:oidc:" + hashlib.sha256(state.encode()).hexdigest()
            assert 0 < await s.service.store.ttl(key) <= 600
            context = json.loads(await s.service.store.get(key))
            payload = {"code": "synthetic-one-use-code", "state": state}
            denied = await client.post(
                "/api/v1/auth/oidc/exchange",
                json=payload,
                headers={"Origin": "https://foreign.example.test"},
            )
            assert denied.status_code == 401
            exchanged = await client.post(
                "/api/v1/auth/oidc/exchange",
                json=payload,
                headers={"Origin": s.settings.public_web_url},
            )
            assert exchanged.status_code == 200, exchanged.text
            assert exchanged.headers["cache-control"] == "no-store"
            assert exchanged.json()["principal"]["actor_id"] == str(s.actor.actor_id)
            replay = await client.post(
                "/api/v1/auth/oidc/exchange",
                json=payload,
                headers={"Origin": s.settings.public_web_url},
            )
            assert replay.status_code == 401
    finally:
        await unused.close()
        await s.service.close()
        await app.state.database.close()


def test_production_rejects_development_login_and_insecure_oidc_web():
    fields = dict(
        _env_file=None,
        env="production",
        identity_provider="oidc",
        oidc_issuer="https://iam.example.test",
        oidc_jwks_url="https://iam.example.test/keys",
        secret_provider="external-secret-provider",  # noqa: S106 - provider mode, not a credential
        local_dev_identity_enabled=False,
    )
    assert Settings(**fields).identity_provider == "oidc"
    with pytest.raises(ValueError, match="prohibit development"):
        Settings(
            **{
                **fields,
                "local_dev_identity_enabled": True,
                "local_dev_signing_key": "synthetic-test-only-key-32-characters",
            }
        )
    with pytest.raises(ValueError, match="require HTTPS"):
        Settings(
            **fields,
            oidc_web_enabled=True,
            oidc_client_id="nxw-web",
            public_web_url="http://portal.example.test",
            oidc_authorization_endpoint="https://iam.example.test/authorize",
            oidc_token_endpoint="https://iam.example.test/token",  # noqa: S106 - synthetic URL
        )
