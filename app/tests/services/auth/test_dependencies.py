from contextlib import contextmanager
from types import SimpleNamespace

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

    app = SimpleNamespace(
        state=SimpleNamespace(settings_provider=lambda: app_settings)
    )
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
