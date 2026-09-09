from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.auth.dependencies as auth_dependencies
from app.core.settings import AppSettings
from app.services.auth.settings import AuthSettings


def test_get_auth_settings_closes_db_session_before_return(monkeypatch) -> None:
    """Effective settingsの解決後、callerへ返す前にDB sessionをcloseすること。"""
    events: list[str] = []
    fake_db = object()
    app_settings = AppSettings()
    resolved = AuthSettings.from_app_settings(app_settings)

    class FakeRuntime:
        @contextmanager
        def managed_session(self):
            events.append("opened")
            try:
                yield fake_db
            finally:
                events.append("closed")

    app = SimpleNamespace(state=SimpleNamespace(settings_provider=lambda: app_settings))
    request = SimpleNamespace(app=app)

    monkeypatch.setattr(
        auth_dependencies,
        "get_app_database_runtime",
        lambda _app: FakeRuntime(),
    )

    def fake_resolve(db, settings):
        assert db is fake_db
        assert settings is app_settings
        events.append("resolved")
        return resolved

    monkeypatch.setattr(auth_dependencies, "resolve_auth_settings", fake_resolve)

    result = auth_dependencies.get_auth_settings(request)  # type: ignore[arg-type]

    assert result is resolved
    assert events == ["opened", "resolved", "closed"]


def test_require_admin_rejects_role_admin_when_local_admin_not_configured() -> None:
    """local admin未設定runtimeでは、正規発行され得ない`role=admin`を拒否すること。

    `local_login`はlocal admin未設定なら`role=admin`を発行しないため、この状態で
    `role=admin`を名乗るsessionはforged cookie以外にあり得ない。publicなdevelopment
    default secretのままでもadmin-only routeを保護できることを確認する回帰test。
    """
    settings = AuthSettings.from_app_settings(
        AppSettings(local_admin_username=None, local_admin_password=None)
    )
    forged_user = {"method": "local_admin", "username": "forged", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        auth_dependencies.require_admin(user=forged_user, settings=settings)

    assert exc_info.value.status_code == 403


def test_require_admin_allows_role_admin_when_local_admin_configured() -> None:
    """local adminが設定済みのruntimeでは、正規発行された`role=admin` sessionを許可すること。"""
    settings = AuthSettings.from_app_settings(
        AppSettings(local_admin_username="admin", local_admin_password="secret")
    )
    admin_user = {"method": "local_admin", "username": "admin", "role": "admin"}

    result = auth_dependencies.require_admin(user=admin_user, settings=settings)

    assert result == admin_user
