"""FastAPI dependencyとして利用する認証・authorization boundary。

OIDC protocol処理そのものはauth serviceへ委譲し、このmoduleではrequest時に利用する
設定の解決、OIDC clientの必須/任意判定、signed session identityのguardを定義する。
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DatabaseRuntimeUnavailableError, get_app_database_runtime
from app.services.auth.config_store import resolve_auth_settings
from app.services.auth.oidc import OIDCClient, OIDCError
from app.services.auth.settings import AuthSettings


def get_runtime_auth_settings(request: Request) -> AuthSettings:
    """Return deployment/runtime auth settings without consulting the shared DB.

    The auth guard and local-admin break-glass path use this dependency so OIDC
    database configuration errors cannot disable local administrator access.
    """
    settings = request.app.state.settings_provider()
    return AuthSettings.from_app_settings(settings)


def get_auth_settings(request: Request) -> AuthSettings:
    """Resolve effective OIDC settings and release the DB session before returning.

    OIDC redirect/callback handlers may await slow provider I/O after this dependency
    completes. Keep the shared-DB read in a short-lived managed session so those
    awaits never retain a checked-out SQLAlchemy connection.
    """
    app_settings = request.app.state.settings_provider()
    runtime = get_app_database_runtime(request.app)
    with runtime.managed_session() as db:
        return resolve_auth_settings(db, app_settings)


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


def get_optional_oidc_client(request: Request) -> OIDCClient | None:
    """logout向けにOIDC clientをbest-effortで返す。

    provider logoutはapplication logoutの付加機能であり、shared DBが停止/fenceしていても
    session破棄を妨げてはならない。そのため通常のDB dependencyを前段に置かず、この関数内で
    DB-backed設定を解決し、DB availability failureはNoneへ縮退する。認証必須の
    redirect/callback endpointにはこのdependencyを使用しない。
    """
    app_settings = request.app.state.settings_provider()
    try:
        runtime = get_app_database_runtime(request.app)
        with runtime.managed_session() as db:
            settings = resolve_auth_settings(db, app_settings)
    except (DatabaseRuntimeUnavailableError, SQLAlchemyError):
        return None

    if not settings.oidc_enabled:
        return None
    try:
        return OIDCClient(settings=settings)
    except OIDCError:
        return None


def require_session_user(
    request: Request,
    settings: AuthSettings = Depends(get_runtime_auth_settings),
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
    settings: AuthSettings = Depends(get_runtime_auth_settings),
) -> Dict[str, Any]:
    """current runtimeで有効なlocal-admin sessionだけに管理操作を許可する。

    OIDC sessionは一般ユーザーidentityとして扱い、現行contractでは自動的にadminへ
    昇格させない。SQLite backup/restoreや認証diagnostics等の管理操作は、このdependency
    を通じてlocal admin sessionだけに限定する。`local_login`は``settings.local_admin_enabled``
    が真の場合にだけ`method=local_admin, role=admin`のsessionを発行するため、
    どちらかがこの形と一致しないsessionは正規発行され得ない。signed sessionの内容だけを
    信頼すると、local admin credential未設定のauth-off runtimeでもdevelopment default
    secretを知るclientがadmin cookieを偽造できるため、current runtimeのlocal admin
    設定と実際のsession内容の両方を要求する。
    """
    if (
        not settings.local_admin_enabled
        or not user
        or user.get("method") != "local_admin"
        or user.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required",
        )
    return user
