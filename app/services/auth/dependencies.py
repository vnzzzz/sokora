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
    """shared DBを参照せずdeployment/runtime authentication settingsを返す。

    auth guardとlocal-admin break-glass pathはこのdependencyを使うため、OIDC DB設定の
    failureがlocal administrator accessを無効化しない。

    Args:
        request: application stateへアクセスするrequest。

    Returns:
        environment/runtime値だけから構築したAuthSettings。
    """
    settings = request.app.state.settings_provider()
    return AuthSettings.from_app_settings(settings)


def get_auth_settings(request: Request) -> AuthSettings:
    """effective OIDC settingsを解決し、DB sessionを返却前にreleaseする。

    OIDC redirect/callback handlerはこのdependency完了後にslow provider I/Oをawaitし得る。
    shared-DB readを短命managed sessionへ閉じ込め、await中にSQLAlchemy connectionを保持しない。

    Args:
        request: application runtime/settingsへアクセスするrequest。

    Returns:
        DB-backed設定とruntime fallbackをprecedence ruleに従って解決したAuthSettings。

    Raises:
        DatabaseRuntimeUnavailableError: shared DB runtimeが利用不能な場合。
        SQLAlchemyError: DB-backed設定読取に失敗した場合。
    """
    app_settings = request.app.state.settings_provider()
    runtime = get_app_database_runtime(request.app)
    with runtime.managed_session() as db:
        return resolve_auth_settings(db, app_settings)


def get_oidc_client(settings: AuthSettings = Depends(get_auth_settings)) -> OIDCClient:
    """OIDC必須endpoint向けclientを返す。

    redirect/callback等はOIDC configurationなしでは意味を持たないため、local adminへ
    暗黙fallbackせずHTTP 400とする。

    Args:
        settings: request時点で解決済みのeffective auth settings。

    Returns:
        有効なOIDC configurationで初期化したOIDCClient。

    Raises:
        HTTPException: OIDCが未設定/無効な場合に400を返す。
        OIDCError: client初期化に必要な設定が成立しない場合。
    """
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC is not configured",
        )
    return OIDCClient(settings=settings)


def get_optional_oidc_client(request: Request) -> OIDCClient | None:
    """logout向けOIDC clientをbest-effortで返す。

    provider logoutはapplication logoutの付加機能であり、shared DBが停止/fenceしていても
    session破棄を妨げてはならない。そのため通常のDB dependencyを前段に置かず、この関数内で
    DB-backed設定を解決し、DB availability failureはNoneへ縮退する。

    Args:
        request: application runtime/settingsへアクセスするrequest。

    Returns:
        利用可能なOIDCClient。DB/config/provider設定を使えない場合は ``None``。
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
    """signed session identityを返し、guard有効時は匿名requestを拒否する。

    `SOKORA_AUTH_ENABLED=false`では匿名利用を許可するためNoneを返し得る。認証有効時は
    sessionの`auth` mappingを必須とし、個別endpointがcookie形式を独自解釈しない。

    Args:
        request: signed sessionへアクセスするrequest。
        settings: runtime-only auth settings。

    Returns:
        session identity mapping。guard無効かつ匿名の場合は ``None``。

    Raises:
        HTTPException: guard有効時にvalidated session identityが無い場合に401を返す。
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

    OIDC sessionは一般ユーザーidentityとして扱い、自動的にadminへ昇格させない。signed session
    だけでなくcurrent runtimeのlocal admin有効状態も要求し、development default secretを知る
    clientによる偽造admin cookieを防ぐ。

    Args:
        user: validated session identity。匿名時は ``None``。
        settings: current runtimeのlocal-admin設定。

    Returns:
        local_admin methodかつadmin roleを持つsession identity。

    Raises:
        HTTPException: local admin未設定、identity欠如、method/role不一致時に403を返す。
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
