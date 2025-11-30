from fastapi import Depends, HTTPException, Request, status

from app.services.auth.oidc import OIDCClient, OIDCError
from app.services.auth.settings import AuthSettings


def get_auth_settings() -> AuthSettings:
    """リクエスト毎に環境変数から最新の設定を構築する"""
    return AuthSettings.from_env()


def get_oidc_client(settings: AuthSettings = Depends(get_auth_settings)) -> OIDCClient:
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC is not configured",
        )
    return OIDCClient(settings=settings)


def get_optional_oidc_client(settings: AuthSettings = Depends(get_auth_settings)) -> OIDCClient | None:
    """OIDC 設定が揃っている場合のみクライアントを返す"""
    if not settings.oidc_enabled:
        return None
    try:
        return OIDCClient(settings=settings)
    except OIDCError:
        return None


def require_session_user(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
) -> dict:
    """API 用の認可依存関係。未認証なら 401 を返す。"""
    user = request.session.get("auth")
    if settings.auth_required and not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user
