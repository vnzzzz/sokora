import logging
import secrets
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.services.auth.dependencies import (
    get_auth_settings,
    get_oidc_client,
    get_optional_oidc_client,
    require_admin,
)
from app.services.auth.oidc import OIDCClient, OIDCError, OIDCStateError
from app.services.auth.settings import AuthSettings

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _safe_next_path(next_path: str | None) -> str:
    """Allow only a same-origin absolute path, never an external redirect."""
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
    settings: AuthSettings = Depends(get_auth_settings),
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
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
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
async def logout(
    request: Request,
    oidc_client: OIDCClient | None = Depends(get_optional_oidc_client),
) -> Response:
    auth_session = request.session.pop("auth", None)
    request.session.pop("auth_error", None)
    request.session.pop("auth_next", None)

    if (
        isinstance(auth_session, dict)
        and auth_session.get("method") == "oidc"
        and oidc_client is not None
    ):
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


@router.get("/settings", response_class=HTMLResponse)
async def auth_settings_page(
    request: Request,
    _admin: dict[str, object] = Depends(require_admin),
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    """Show shared, read-only authentication diagnostics to administrators."""
    context = {"request": request, "settings": settings}
    return templates.TemplateResponse("pages/auth/settings.html", context)
