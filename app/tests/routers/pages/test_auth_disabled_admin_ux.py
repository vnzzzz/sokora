import pytest


@pytest.mark.asyncio
async def test_auth_off_anonymous_can_login_and_logout_local_admin(
    async_client, monkeypatch
) -> None:
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "false")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    anonymous_page = await async_client.get("/")
    assert anonymous_page.status_code == 200
    assert 'data-testid="admin-login-entry"' in anonymous_page.text
    assert 'href="/auth/login/admin?next=/"' in anonymous_page.text

    login_response = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/"

    admin_page = await async_client.get("/")
    assert admin_page.status_code == 200
    assert 'data-testid="admin-login-entry"' not in admin_page.text
    assert 'href="/admin/auth"' in admin_page.text

    logout_response = await async_client.post("/auth/logout", follow_redirects=False)
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/"

    anonymous_again = await async_client.get("/")
    assert anonymous_again.status_code == 200
    assert 'data-testid="admin-login-entry"' in anonymous_again.text


@pytest.mark.asyncio
async def test_auth_off_hides_admin_login_when_local_admin_is_unconfigured(
    async_client, monkeypatch
) -> None:
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "false")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.delenv("SOKORA_LOCAL_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("SOKORA_LOCAL_ADMIN_PASSWORD", raising=False)

    response = await async_client.get("/")

    assert response.status_code == 200
    assert 'data-testid="admin-login-entry"' not in response.text


@pytest.mark.asyncio
async def test_auth_on_local_admin_logout_keeps_login_redirect(
    async_client, monkeypatch
) -> None:
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    login_response = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    logout_response = await async_client.post("/auth/logout", follow_redirects=False)

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/auth/login?next=%2F&reason=logout"
