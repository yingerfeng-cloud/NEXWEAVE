"""Browser login bootstrap, separate from authenticated resource APIs."""

from typing import cast

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from nexweave_api.errors import ApiProblem
from nexweave_api.identity import LocalDevIdentityProvider
from nexweave_api.settings import Settings
from nexweave_api.web_auth import COOKIE, COOKIE_PATH, TTL, BrowserOidc, append_query
from nexweave_contracts.web_auth import OidcCodeExchange, WebAuthConfig, WebSessionResponse

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get("/config", response_model=WebAuthConfig)
async def configuration(request: Request, response: Response) -> WebAuthConfig:
    settings = cast(Settings, request.app.state.settings)
    response.headers["Cache-Control"] = "no-store"
    local = (
        settings.env == "development"
        and settings.identity_provider == "local"
        and settings.local_dev_identity_enabled
    )
    return WebAuthConfig(
        provider="oidc" if settings.identity_provider == "oidc" else "local",
        issuer=settings.oidc_issuer
        if settings.identity_provider == "oidc"
        else LocalDevIdentityProvider.issuer,
        login_enabled=local or settings.oidc_web_enabled,
        login_url="/api/v1/auth/oidc/login" if settings.oidc_web_enabled else None,
        logout_url="/api/v1/auth/oidc/logout"
        if settings.oidc_web_enabled and settings.oidc_end_session_endpoint
        else None,
    )


def _browser(request: Request) -> BrowserOidc:
    service = cast(BrowserOidc | None, request.app.state.browser_oidc)
    if service is None:
        raise ApiProblem(
            503, "OIDC_WEB_UNAVAILABLE", "OIDC Web unavailable", "OIDC Web login is not configured."
        )
    return service


@router.get("/oidc/login")
async def start_login(request: Request) -> RedirectResponse:
    service = _browser(request)
    target, binding = await service.start()
    response = RedirectResponse(
        target,
        status_code=302,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
    response.set_cookie(
        COOKIE,
        binding,
        path=COOKIE_PATH,
        max_age=TTL,
        httponly=True,
        secure=service.settings.public_web_url.startswith("https://"),
        samesite="lax",
    )
    return response


@router.post("/oidc/exchange", response_model=WebSessionResponse)
async def exchange(
    request: Request, response: Response, body: OidcCodeExchange
) -> WebSessionResponse:
    session = await _browser(request).exchange(
        code=body.code,
        state=body.state,
        binding=request.cookies.get(COOKIE, ""),
        origin=request.headers.get("Origin", ""),
    )
    response.headers.update({"Cache-Control": "no-store", "Pragma": "no-cache"})
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    return WebSessionResponse.model_validate(session)


@router.get("/oidc/logout")
async def logout(request: Request) -> RedirectResponse:
    service = _browser(request)
    service.require_enabled()
    settings = service.settings
    if not settings.oidc_end_session_endpoint:
        raise ApiProblem(
            409,
            "OIDC_LOGOUT_UNAVAILABLE",
            "SSO logout unavailable",
            "Only the current Web session was cleared.",
        )
    target = append_query(
        settings.oidc_end_session_endpoint,
        {
            "client_id": settings.oidc_client_id,
            "post_logout_redirect_uri": settings.public_web_url.rstrip("/") + "/",
        },
    )
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store"})
