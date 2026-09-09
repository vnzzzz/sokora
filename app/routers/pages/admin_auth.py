"""Local admin向けauthentication / OIDC設定画面。

認証protocol flowは `/auth/*` に残し、configuration UIは `/admin/*` namespaceへ分離する。
このrouter配下はすべてlocal admin sessionを必須とする。
"""

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_app_database_runtime, get_db
from app.services.auth.config_store import (
    AuthConfigError,
    OIDCDiscoveryError,
    check_oidc_discovery,
    save_oidc_config,
    unlink_oidc_config,
    validate_oidc_scope_for_enable,
)
from app.services.auth.dependencies import (
    get_auth_settings,
    get_runtime_auth_settings,
    require_admin,
)
from app.services.auth.settings import AuthSettings

router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin"],
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
templates = Jinja2Templates(directory="app/templates")

_AUTH_SETTINGS_CSRF_SESSION_KEY = "auth_settings_csrf_token"


def _auth_settings_csrf_token(request: Request) -> str:
    """Return a stable per-session CSRF token for admin OIDC settings forms."""
    token = request.session.get(_AUTH_SETTINGS_CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        request.session[_AUTH_SETTINGS_CSRF_SESSION_KEY] = token
    return token


def _require_auth_settings_csrf(request: Request, submitted_token: str) -> None:
    """Reject state-changing auth-settings requests without the session token."""
    expected_token = request.session.get(_AUTH_SETTINGS_CSRF_SESSION_KEY)
    if (
        not isinstance(expected_token, str)
        or not submitted_token
        or not secrets.compare_digest(
            submitted_token.encode("utf-8"),
            expected_token.encode("utf-8"),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


def _settings_form_values(
    request: Request,
    settings: AuthSettings,
) -> dict[str, object]:
    """Return non-secret form values, preserving a failed/tested candidate once."""
    pending = request.session.pop("auth_settings_form", None)
    if isinstance(pending, dict):
        return pending
    configured_enabled = (
        settings.oidc_enabled
        if settings.oidc_enabled_override is None
        else settings.oidc_enabled_override
    )
    return {
        "enabled": configured_enabled,
        "issuer": settings.oidc_issuer or "",
        "client_id": settings.oidc_client_id or "",
        "scope": settings.oidc_scope,
    }


def _remember_settings_form(
    request: Request,
    *,
    enabled: bool,
    issuer: str,
    client_id: str,
    scope: str,
) -> None:
    """Persist only non-secret candidate fields across a redirect."""
    request.session["auth_settings_form"] = {
        "enabled": enabled,
        "issuer": issuer,
        "client_id": client_id,
        "scope": scope,
    }


@router.get("", response_class=HTMLResponse)
async def auth_settings_page(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    """Show and edit shared OIDC settings for local administrators."""
    context = {
        "request": request,
        "settings": settings,
        "form_values": _settings_form_values(request, settings),
        "notice": request.session.pop("auth_settings_notice", None),
        "error_message": request.session.pop("auth_settings_error", None),
        "csrf_token": _auth_settings_csrf_token(request),
    }
    return templates.TemplateResponse("pages/admin/auth.html", context)


@router.post("/oidc")
async def save_auth_oidc_settings(
    request: Request,
    enabled: bool = Form(False),
    issuer: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    scope: str = Form("openid profile email"),
    csrf_token: str = Form(""),
) -> Response:
    """Validate external discovery first, then persist through a short DB session."""
    _require_auth_settings_csrf(request, csrf_token)
    app_settings = request.app.state.settings_provider()
    try:
        if enabled:
            validate_oidc_scope_for_enable(scope)
            await check_oidc_discovery(issuer, app_settings.oidc_http_timeout)
        runtime = get_app_database_runtime(request.app)
        with runtime.managed_session() as db:
            save_oidc_config(
                db,
                app_settings,
                enabled=enabled,
                issuer=issuer,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
            )
    except AuthConfigError as exc:
        _remember_settings_form(
            request,
            enabled=enabled,
            issuer=issuer,
            client_id=client_id,
            scope=scope,
        )
        request.session["auth_settings_error"] = str(exc)
    else:
        request.session["auth_settings_notice"] = "OIDC設定を保存しました。"
    return RedirectResponse("/admin/auth", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/oidc/test")
async def test_auth_oidc_settings(
    request: Request,
    enabled: bool = Form(False),
    issuer: str = Form(""),
    client_id: str = Form(""),
    scope: str = Form("openid profile email"),
    csrf_token: str = Form(""),
    settings: AuthSettings = Depends(get_runtime_auth_settings),
) -> Response:
    """Check standard OIDC discovery for an unsaved issuer candidate."""
    _require_auth_settings_csrf(request, csrf_token)
    _remember_settings_form(
        request,
        enabled=enabled,
        issuer=issuer,
        client_id=client_id,
        scope=scope,
    )
    try:
        await check_oidc_discovery(issuer, settings.oidc_http_timeout)
    except OIDCDiscoveryError as exc:
        request.session["auth_settings_error"] = str(exc)
    else:
        request.session["auth_settings_notice"] = "OIDC discoveryへ接続できました。"
    return RedirectResponse("/admin/auth", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/oidc/unlink")
async def unlink_auth_oidc_settings(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    """Explicitly disable and clear DB OIDC settings without env fallback."""
    _require_auth_settings_csrf(request, csrf_token)
    unlink_oidc_config(db)
    request.session["auth_settings_notice"] = "OIDC連携を解除しました。"
    request.session.pop("auth_settings_form", None)
    return RedirectResponse("/admin/auth", status_code=status.HTTP_303_SEE_OTHER)
