import logging
import secrets
import urllib.parse

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.services.auth.dependencies import (
    get_auth_settings,
    get_oidc_client,
    get_optional_oidc_client,
)
from app.services.auth.oidc import OIDCClient, OIDCError
from app.services.auth.settings import AuthSettings
from app.services.auth.state import AuthState, AuthStateStore

router = APIRouter(prefix="/auth", tags=["Auth"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _safe_next_path(next_path: str | None) -> str:
    if not next_path:
        return "/"
    if not next_path.startswith("/"):
        return "/"
    return next_path


def _require_local_admin(request: Request) -> None:
    auth = request.session.get("auth")
    if not (
        isinstance(auth, dict)
        and auth.get("method") == "local_admin"
        and auth.get("role") == "admin"
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _get_state_store() -> AuthStateStore:
    return AuthStateStore()


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str | None = None,
    reason: str | None = None,
    next: str = "/",
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    message: str | None = None
    session_error = request.session.pop("auth_error", None)
    if session_error:
        message = session_error
    elif error == "oidc":
        message = (
            "Keycloak でのログインに失敗しました。"
            "管理者ログインか後ほどお試しください。"
        )
    elif error == "local":
        message = "ローカル管理者ログインに失敗しました。"
    elif reason == "reauth":
        message = "セッションが切れました。再度ログインしてください。"
    elif reason == "logout":
        message = "ログアウトしました。"

    context = {
        "request": request,
        "next_path": _safe_next_path(next),
        "local_enabled": settings.local_admin_enabled,
        "oidc_enabled": settings.oidc_enabled,
        "oidc_toggle_enabled": settings.oidc_toggle_enabled,
        "error_message": message,
    }
    return templates.TemplateResponse("pages/auth/login.html", context)


@router.get("/login/admin", response_class=HTMLResponse)
async def admin_login_page(
    request: Request,
    error: str | None = None,
    next: str = "/",
    settings: AuthSettings = Depends(get_auth_settings),
) -> Response:
    message: str | None = None
    session_error = request.session.pop("auth_error", None)
    if session_error:
        message = session_error
    elif error == "local":
        message = "管理者ログインに失敗しました。"

    context = {
        "request": request,
        "next_path": _safe_next_path(next),
        "local_enabled": settings.local_admin_enabled,
        "error_message": message,
    }
    return templates.TemplateResponse("pages/auth/admin_login.html", context)


@router.get("/redirect")
async def oidc_redirect(
    request: Request,
    next: str = "/",
    settings: AuthSettings = Depends(get_auth_settings),
    oidc_client: OIDCClient = Depends(get_oidc_client),
) -> Response:
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC is not configured"
        )
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    request.session["oidc_state"] = state
    request.session["oidc_nonce"] = nonce
    request.session["auth_next"] = _safe_next_path(next)
    try:
        redirect_url = oidc_client.build_authorization_url(state=state, nonce=nonce)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to build authorization URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to start OIDC login"
        ) from exc
    return RedirectResponse(url=redirect_url, status_code=307)


@router.get("/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    settings: AuthSettings = Depends(get_auth_settings),
    oidc_client: OIDCClient = Depends(get_oidc_client),
) -> Response:
    saved_state = request.session.pop("oidc_state", None)
    nonce = request.session.pop("oidc_nonce", None)
    next_path = request.session.pop("auth_next", "/")

    if not code or not state or not saved_state or state != saved_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OIDC state or code"
        )

    try:
        result = oidc_client.exchange_code(
            code=code,
            state=state,
            nonce=nonce or "",
            redirect_uri=settings.oidc_redirect_uri,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("OIDC callback failed: %s", exc)
        request.session["auth_error"] = (
            "Keycloak でのログインに失敗しました。"
            "ローカル管理者でログインしてください。"
        )
        login_url = f"/auth/login?error=oidc&next={urllib.parse.quote(next_path)}"
        return RedirectResponse(url=login_url, status_code=303)

    request.session["auth"] = {
        "method": "oidc",
        "subject": result.subject,
        "username": result.username,
        "id_token": result.id_token,
    }
    return RedirectResponse(url=next_path, status_code=303)


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
            detail="Local admin login is not configured",
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
        target = _safe_next_path(next)
        return RedirectResponse(url=target, status_code=303)

    request.session["auth_error"] = "管理者認証に失敗しました。"
    return RedirectResponse(
        url=f"/auth/login/admin?error=local&next={urllib.parse.quote(_safe_next_path(next))}",
        status_code=303,
    )


@router.post("/logout")
async def logout(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
    oidc_client: OIDCClient | None = Depends(get_optional_oidc_client),
) -> Response:
    auth_session = request.session.get("auth")
    id_token = auth_session.get("id_token") if isinstance(auth_session, dict) else None
    request.session.clear()

    if auth_session and auth_session.get("method") == "oidc" and id_token and oidc_client:
        try:
            post_logout_redirect = f"{request.url_for('login_page')}?reason=logout"
            logout_url = oidc_client.get_logout_url(
                id_token_hint=id_token,
                post_logout_redirect_uri=post_logout_redirect,
            )
            if logout_url:
                return RedirectResponse(url=logout_url, status_code=303)
        except OIDCError as exc:
            logger.warning("OIDC logout failed, falling back to local logout: %s", exc)
    return RedirectResponse(url="/auth/login?reason=logout", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def auth_settings_page(
    request: Request,
    info: str | None = None,
    state_store: AuthStateStore = Depends(_get_state_store),
) -> Response:
    _require_local_admin(request)
    flash_info = request.session.pop("auth_info", None)
    message = flash_info or info
    state = state_store.load_state()
    context = {
        "request": request,
        "state": state,
        "message": message,
    }
    return templates.TemplateResponse("pages/auth/settings.html", context)


@router.post("/settings/oidc/toggle")
async def toggle_oidc(
    request: Request,
    enabled: bool = Form(False),
    state_store: AuthStateStore = Depends(_get_state_store),
) -> Response:
    _require_local_admin(request)
    state_store.save_state(AuthState(oidc_enabled=enabled))
    request.session["auth_info"] = "OIDC 設定を更新しました。"
    return RedirectResponse(url="/auth/settings", status_code=303)
