"""FastAPI dependencyとして利用する認証・authorization boundary。

OIDC protocol処理そのものはauth serviceへ委譲し、このmoduleではrequest時に利用する
設定の解決、OIDC clientの必須/任意判定、signed session identityのguardを定義する。
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status

from app.services.auth.oidc import OIDCClient, OIDCError
from app.services.auth.settings import AuthSettings


def get_auth_settings(request: Request) -> AuthSettings:
    """applicationのsettings providerからrequest用認証設定を構築する。

    dependency自身は``os.environ``を直接参照せず、application factoryが選んだproviderを
    経由する。default providerは呼び出し時にenvironmentから新しいAppSettingsを構築し得るが、
    このdependencyはrequestごとにstartup security validationを再実行しない。

    SessionMiddleware等にはapplication作成時に固定される設定もあるため、running processの
    environment変更を認証設定のhot-reload手段として扱わない。runtime config変更はprocess
    restartで一貫して適用する。
    """
    settings = request.app.state.settings_provider()
    return AuthSettings.from_app_settings(settings)


def get_oidc_client(settings: AuthSettings = Depends(get_auth_settings)) -> OIDCClient:
    """OIDCが必須のendpoint向けにclientを返し、未設定ならrequestを拒否する。

    redirect/callback等はOIDC configurationなしでは意味を持たないため、local adminへ
    暗黙fallbackせずHTTP 400とする。認証経路の選択はlogin UI/callerが明示的に行う。
    """
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC is not configured",
        )
    return OIDCClient(settings=settings)


def get_optional_oidc_client(
    settings: AuthSettings = Depends(get_auth_settings),
) -> OIDCClient | None:
    """logout等、OIDC連携が利用可能な場合だけclientを返す。

    OIDCが無効またはmetadata/client初期化に失敗しても、application sessionのlogout等
    provider非依存の処理は継続できるためNoneへ縮退する。このdependencyを認証必須の
    redirect/callback endpointには使用しない。
    """
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
    """signed session identityを返し、認証guard有効時は匿名requestを401で拒否する。

    `SOKORA_AUTH_ENABLED=false`では匿名利用を許可するためNoneを返し得る。認証が有効な
    runtimeではsessionの`auth` mappingを必須とし、個別endpointが独自にcookie形式を
    解釈しないための共通boundaryとして使う。
    """
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
    """local-admin-only操作に共通の`role=admin` authorizationを強制する。

    OIDC sessionは一般ユーザーidentityとして扱い、現行contractでは自動的にadminへ
    昇格させない。SQLite backup/restoreや認証diagnostics等の管理操作は、このdependency
    を通じてlocal admin sessionだけに限定する。
    """
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required",
        )
    return user
