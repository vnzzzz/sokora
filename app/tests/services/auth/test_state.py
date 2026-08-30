from pathlib import Path

from fastapi.testclient import TestClient

from app.core.settings import AppSettings
from app.main import create_application
from app.services.auth.state import AuthState, AuthStateStore


def test_auth_state_store_uses_explicit_path(
    monkeypatch, tmp_path: Path
) -> None:
    env_path = tmp_path / "environment-state.json"
    explicit_path = tmp_path / "explicit-state.json"
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(env_path))

    store = AuthStateStore(explicit_path)
    store.save_state(AuthState(oidc_enabled=False))

    assert explicit_path.exists()
    assert not env_path.exists()
    assert store.load_state().oidc_enabled is False


def test_oidc_toggle_uses_explicit_application_state_path(tmp_path: Path) -> None:
    state_path = tmp_path / "auth-state.json"
    database_path = tmp_path / "sokora.db"
    settings = AppSettings(
        database_url=f"sqlite:///{database_path}",
        session_secret="test-secret",
        auth_state_path=state_path,
        local_auth_enabled=True,
        local_admin_username="admin",
        local_admin_password="secret",
    )
    app = create_application(settings)

    with TestClient(app) as client:
        login_response = client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/"},
            follow_redirects=False,
        )
        assert login_response.status_code == 303

        toggle_response = client.post(
            "/auth/settings/oidc/toggle",
            data={"enabled": "false"},
            follow_redirects=False,
        )
        assert toggle_response.status_code == 303

    assert AuthStateStore(state_path).load_state().oidc_enabled is False
