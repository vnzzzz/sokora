from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status

from app.services.auth.oidc import OIDCClient, OIDCError
from app.services.auth.settings import AuthSettings


def get_auth_settings(request: Request) -> AuthSettings:
    """Build request auth settings from the application's shared settings provider."""
    settings = request.app.state.settings_provider()
    return AuthSettings.from_app_settings(settings)


def get_oidc_client(settings: AuthSettings = Depends(get_auth_settings)) -> OIDCClient:
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC is not configured",
        )
    return OIDCClient(settings=settings)


def get_optional_oidc_client(
    settings: AuthSettings = Depends(get_auth_settings),
) -> OIDCClient | None:
    if not settings.oidc_enabled:
        return None
    try:
        return OIDCClient(settings=settings)
    except OIDCError:
        return None


def require_session_user(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
) -> Dict[str, Any] | None:
    """Return the signed session identity or reject when auth is required."""
    user = request.session.get("auth")
    if settings.auth_enabled and not isinstance(user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return user if isinstance(user, dict) else None


def require_admin(
    user: Dict[str, Any] | None = Depends(require_session_user),
) -> Dict[str, Any]:
    """Common authorization policy for local-admin-only routes."""
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required",
        )
    return user
