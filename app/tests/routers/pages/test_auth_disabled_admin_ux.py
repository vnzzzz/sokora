from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.settings import AppSettings
from app.main import create_application


def _create_auth_app(
    *,
    auth_enabled: bool,
    local_admin_username: str | None = "admin",
    local_admin_password: str | None = "secret",
) -> FastAPI:
    return create_application(
        AppSettings(
            database_url="sqlite:///:memory:",
            auth_enabled=auth_enabled,
            session_secret="test-session-secret-for-auth-disabled-admin-ux",
            local_auth_enabled=True,
            local_admin_username=local_admin_username,
            local_admin_password=local_admin_password,
        )
    )


def test_auth_off_anonymous_can_login_and_logout_local_admin() -> None:
    application = _create_auth_app(auth_enabled=False)

    with TestClient(application) as client:
        anonymous_page = client.get("/")
        assert anonymous_page.status_code == 200
        assert 'data-testid="admin-login-entry"' in anonymous_page.text
        assert 'href="/auth/login/admin?next=/"' in anonymous_page.text

        login_response = client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/"},
            follow_redirects=False,
        )
        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/"

        admin_page = client.get("/")
        assert admin_page.status_code == 200
        assert 'data-testid="admin-login-entry"' not in admin_page.text
        assert 'href="/admin/auth"' in admin_page.text

        logout_response = client.post("/auth/logout", follow_redirects=False)
        assert logout_response.status_code == 303
        assert logout_response.headers["location"] == "/"

        anonymous_again = client.get("/")
        assert anonymous_again.status_code == 200
        assert 'data-testid="admin-login-entry"' in anonymous_again.text


def test_auth_off_hides_admin_login_when_local_admin_is_unconfigured() -> None:
    application = _create_auth_app(
        auth_enabled=False,
        local_admin_username=None,
        local_admin_password=None,
    )

    with TestClient(application) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'data-testid="admin-login-entry"' not in response.text


def test_auth_on_local_admin_logout_keeps_login_redirect() -> None:
    application = _create_auth_app(auth_enabled=True)

    with TestClient(application) as client:
        login_response = client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/"},
            follow_redirects=False,
        )
        assert login_response.status_code == 303

        logout_response = client.post("/auth/logout", follow_redirects=False)

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/auth/login?next=%2F&reason=logout"
