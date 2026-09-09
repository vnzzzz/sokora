import logging
import secrets
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth.config_store import (
    AuthConfigError,
    OIDCDiscoveryError,
    check_oidc_discovery,
    save_oidc_config,
    unlink_oidc_config,
)
from app.services.auth.dependencies import (
    get_auth_settings,
    get_oidc_client,
    get_optional_oidc_client,
    get_runtime_auth_settings,
    require_admin,
)
from app.services.auth.oidc import OIDCClient, OIDCError, OIDCStateError
from app.services.auth.settings import AuthSettings

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _safe_next_path(next_path: str | None) -> str:
    """login/logout後の戻り先をsame-origin absolute pathだけへ制限する。

    scheme/netloc、protocol-relative path、backslashを含む値はrootへ縮退する。fragmentは
    server redirectに不要なため捨て、pathとqueryだけを保持する。sessionに保存したnextも
    callback直前に再度このfunctionへ通し、client入力をopen redirectへ変換しない。
    """
    if not next_path or "\\" in next_path:
        return "/"
    parsed = urlsplit(next_path)
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
    ):
        return "/"
    return urlunsplit(("", "", parsed.path, parsed.query, ""))


def _login_url(*, next_path: str = "/", reason: str | None = None) -> str:
    query: dict[str, str] = {"next": _safe_next_path(next_path)}
    if reason:
        query["reason"] = reason
    return f"/auth/login?{urlencode(query)}"


def _admin_login_url(*, next_path: str = "/", reason: str | None = None) -> str:
    query: dict[str, str] = {"next": _safe_next_path(next_path)}
    if reason:
        query["reason"] = reason
    return f"/auth/login/admin?{urlencode(query)}"


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "/",
    reason: str | None = None,
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    del reason
    context = {
        "request": request,
        "next_path": _safe_next_path(next),
        "local_enabled": settings.local_admin_enabled,
        "oidc_enabled": settings.oidc_enabled,
        "error_message": request.session.pop("auth_error", None),
    }
    return templates.TemplateResponse("pages/auth/login.html", context)


@router.get("/login/admin", response_class=HTMLResponse)
async def admin_login_page(
    request: Request,
    next: str = "/",
    settings: AuthSettings = Depends(get_runtime_auth_settings),
) -> Response:
    context = {
        "request": request,
        "next_path": _safe_next_path(next),
        "local_enabled": settings.local_admin_enabled,
        "error_message": request.session.pop("auth_error", None),
    }
    return templates.TemplateResponse("pages/auth/admin_login.html", context)


@router.get("/redirect")
async def oidc_redirect(
    request: Request,
    next: str = "/",
    oidc_client: OIDCClient = Depends(get_oidc_client),
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    """OIDC authorization flowを開始し、安全な戻り先をsigned sessionへ一時保存する。

    OAuth state/OIDC nonceの生成・保持はOIDC client/Authlibへ委譲する。provider discoveryが
    失敗した場合は一時next stateを破棄してlogin画面へ戻し、local adminへ自動failoverは
    しない。
    """
    request.session["auth_next"] = _safe_next_path(next)
    try:
        target = await oidc_client.build_authorization_url(
            request=request,
            redirect_uri=settings.oidc_redirect_uri,
        )
    except OIDCError as exc:
        logger.warning("OIDC authorization redirect failed: %s", exc)
        request.session.pop("auth_next", None)
        request.session["auth_error"] = "SSOへ接続できませんでした。"
        return RedirectResponse(
            _login_url(next_path=next, reason="oidc_unavailable"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/callback")
async def oidc_callback(
    request: Request,
    oidc_client: OIDCClient = Depends(get_oidc_client),
) -> Response:
    """OIDC callbackを検証し、validated identityだけをapplication sessionへ保存する。

    code exchange時のstate/nonce/ID token validationはOIDC clientへ委譲する。persistent session
    にはaccess/refresh/ID tokenを保持せず、subjectと表示用usernameだけを保存する。state
    mismatchは認証失敗として400にし、通常provider failureとは区別する。
    """
    next_path = _safe_next_path(request.session.pop("auth_next", "/"))
    try:
        result = await oidc_client.exchange_code(request=request)
    except OIDCStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OIDC callback state",
        ) from exc
    except OIDCError as exc:
        logger.warning("OIDC callback failed: %s", exc)
        request.session["auth_error"] = "SSO認証に失敗しました。"
        return RedirectResponse(
            _login_url(next_path=next_path, reason="oidc_failed"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    request.session["auth"] = {
        "method": "oidc",
        "subject": result.subject,
        "username": result.username,
    }
    request.session.pop("auth_error", None)
    return RedirectResponse(next_path, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/local")
async def local_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    settings: AuthSettings = Depends(get_runtime_auth_settings),
) -> Response:
    """configured local admin credentialを照合し、admin role付きsessionを発行する。

    local auth flagとusername/passwordが揃わないruntimeでは経路自体を利用不可とする。
    credentialはconstant-time compareで照合し、成功したlocal sessionだけへ``role=admin``
    を付与する。一般user向けlocal identityやOIDC失敗からの自動fallbackは提供しない。
    """
    if not settings.local_admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local admin authentication is not configured",
        )

    expected_user = settings.local_admin_username or ""
    expected_password = settings.local_admin_password or ""
    if secrets.compare_digest(username, expected_user) and secrets.compare_digest(
        password, expected_password
    ):
        request.session["auth"] = {
            "method": "local_admin",
            "username": username,
            "role": "admin",
        }
        request.session.pop("auth_error", None)
        return RedirectResponse(
            _safe_next_path(next), status_code=status.HTTP_303_SEE_OTHER
        )

    request.session["auth_error"] = "管理者認証に失敗しました。"
    return RedirectResponse(
        _admin_login_url(next_path=next, reason="local_failed"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/logout")
async def logout(request: Request) -> Response:
    """application sessionを最初のresponseで破棄し、その後だけprovider logoutへ進む。

    shared DB / IdPはapplication logoutのcritical pathへ置かない。OIDC sessionの場合も、
    authenticated identityを含まないcookieをclientへ返してから別requestでprovider logoutを
    best-effort実行する。これによりDB接続がblack-holeしてもlocal logout完了をblockしない。
    """
    auth_session = request.session.get("auth")
    was_oidc = isinstance(auth_session, dict) and auth_session.get("method") == "oidc"

    request.session.clear()
    if was_oidc:
        request.session["logout_pending"] = True
        return RedirectResponse(
            "/auth/logout/provider",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        _login_url(reason="logout"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout/provider")
async def oidc_provider_logout(
    request: Request,
    oidc_client: OIDCClient | None = Depends(get_optional_oidc_client),
) -> Response:
    """local logout完了後にだけprovider logoutをbest-effortで開始する。"""
    if request.session.pop("logout_pending", None) is not True:
        request.session.clear()
        return RedirectResponse(
            _login_url(reason="logout"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if oidc_client is not None:
        callback_url = str(request.url_for("oidc_logout_callback"))
        try:
            logout_url = await oidc_client.get_logout_url(
                request=request,
                post_logout_redirect_uri=callback_url,
            )
        except OIDCError as exc:
            logger.warning("OIDC logout failed: %s", exc)
            logout_url = None
        if logout_url:
            return RedirectResponse(logout_url, status_code=status.HTTP_303_SEE_OTHER)

    request.session.clear()
    return RedirectResponse(
        _login_url(reason="logout"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout/callback", name="oidc_logout_callback")
async def oidc_logout_callback(
    request: Request,
    oidc_client: OIDCClient | None = Depends(get_optional_oidc_client),
) -> Response:
    """provider logout callback stateを検証し、残存application sessionを消去する。

    state mismatchは400として拒否する。provider metadata/validationの一般failureはlogへ残すが、
    logout後のapplication sessionを復活させる理由にはせず最終的にclearする。
    """
    if oidc_client is not None:
        try:
            await oidc_client.validate_logout_response(request)
        except OIDCStateError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OIDC logout state",
            ) from exc
        except OIDCError as exc:
            logger.warning("OIDC logout callback failed: %s", exc)
    request.session.clear()
    return RedirectResponse(
        _login_url(reason="logout"),
        status_code=status.HTTP_303_SEE_OTHER,
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


@router.get("/settings", response_class=HTMLResponse)
async def auth_settings_page(
    request: Request,
    _admin: dict[str, object] = Depends(require_admin),
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    """Show and edit shared OIDC settings for local administrators."""
    context = {
        "request": request,
        "settings": settings,
        "form_values": _settings_form_values(request, settings),
        "notice": request.session.pop("auth_settings_notice", None),
        "error_message": request.session.pop("auth_settings_error", None),
    }
    return templates.TemplateResponse("pages/auth/settings.html", context)


@router.post("/settings/oidc")
async def save_auth_oidc_settings(
    request: Request,
    enabled: bool = Form(False),
    issuer: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    scope: str = Form("openid profile email"),
    _admin: dict[str, object] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Persist OIDC configuration without ever echoing the client secret."""
    app_settings = request.app.state.settings_provider()
    try:
        if enabled:
            await check_oidc_discovery(issuer, app_settings.oidc_http_timeout)
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
    return RedirectResponse("/auth/settings", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/oidc/test")
async def test_auth_oidc_settings(
    request: Request,
    enabled: bool = Form(False),
    issuer: str = Form(""),
    client_id: str = Form(""),
    scope: str = Form("openid profile email"),
    _admin: dict[str, object] = Depends(require_admin),
    settings: AuthSettings = Depends(get_runtime_auth_settings),
) -> Response:
    """Check standard OIDC discovery for an unsaved issuer candidate."""
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
    return RedirectResponse("/auth/settings", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/oidc/unlink")
async def unlink_auth_oidc_settings(
    request: Request,
    _admin: dict[str, object] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Explicitly disable and clear DB OIDC settings without env fallback."""
    unlink_oidc_config(db)
    request.session["auth_settings_notice"] = "OIDC連携を解除しました。"
    request.session.pop("auth_settings_form", None)
    return RedirectResponse("/auth/settings", status_code=status.HTTP_303_SEE_OTHER)
