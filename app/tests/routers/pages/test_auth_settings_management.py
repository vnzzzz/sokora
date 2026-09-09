from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from app.db.session import create_database_runtime, initialize_database


async def _login_admin(async_client, monkeypatch) -> None:
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    response = await async_client.post(
        "/auth/local",
        data={
            "username": "admin",
            "password": "secret",
            "next": "/auth/settings",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/settings"


@pytest.mark.asyncio
async def test_auth_settings_uses_legacy_environment_until_db_row_exists(
    async_client, monkeypatch
) -> None:
    monkeypatch.setenv("OIDC_ISSUER", "https://legacy.example/realms/sokora")
    monkeypatch.setenv("OIDC_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    await _login_admin(async_client, monkeypatch)

    settings_page = await async_client.get("/auth/settings")
    assert settings_page.status_code == 200
    assert 'data-testid="oidc-config-source">legacy_environment<' in settings_page.text
    assert 'action="/auth/settings/oidc"' in settings_page.text
    assert 'name="issuer"' in settings_page.text
    assert 'name="client_id"' in settings_page.text
    assert 'name="client_secret"' in settings_page.text
    assert "legacy-secret" not in settings_page.text

    login_page = await async_client.get("/auth/login")
    assert login_page.status_code == 200
    assert "/auth/redirect" in login_page.text


@pytest.mark.asyncio
async def test_db_oidc_settings_encrypt_secret_and_become_source_of_truth(
    async_client, db, monkeypatch
) -> None:
    monkeypatch.setenv("OIDC_ISSUER", "https://legacy.example/realms/sokora")
    monkeypatch.setenv("OIDC_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv(
        "SOKORA_AUTH_CONFIG_ENCRYPTION_KEY",
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    )

    await _login_admin(async_client, monkeypatch)

    save = await async_client.post(
        "/auth/settings/oidc",
        data={
            "enabled": "true",
            "issuer": "https://db.example/realms/sokora",
            "client_id": "db-client",
            "client_secret": "db-secret",
            "scope": "openid profile email",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303
    assert save.headers["location"] == "/auth/settings"

    row = db.execute(
        text(
            "SELECT oidc_enabled, oidc_issuer, oidc_client_id, "
            "oidc_client_secret_encrypted, oidc_scope "
            "FROM auth_config WHERE id = 1"
        )
    ).one()
    assert row.oidc_enabled in {1, True}
    assert row.oidc_issuer == "https://db.example/realms/sokora"
    assert row.oidc_client_id == "db-client"
    assert row.oidc_client_secret_encrypted != "db-secret"
    assert "db-secret" not in row.oidc_client_secret_encrypted
    assert row.oidc_scope == "openid profile email"

    settings_page = await async_client.get("/auth/settings")
    assert settings_page.status_code == 200
    assert 'data-testid="oidc-config-source">database<' in settings_page.text
    assert "https://db.example/realms/sokora" in settings_page.text
    assert "db-client" in settings_page.text
    assert "db-secret" not in settings_page.text
    assert "legacy-secret" not in settings_page.text


@pytest.mark.asyncio
async def test_db_disabled_oidc_never_falls_back_to_legacy_environment(
    async_client, monkeypatch
) -> None:
    monkeypatch.setenv("OIDC_ISSUER", "https://legacy.example/realms/sokora")
    monkeypatch.setenv("OIDC_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    await _login_admin(async_client, monkeypatch)

    save = await async_client.post(
        "/auth/settings/oidc",
        data={
            "enabled": "false",
            "issuer": "",
            "client_id": "",
            "client_secret": "",
            "scope": "openid profile email",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303

    settings_page = await async_client.get("/auth/settings")
    assert settings_page.status_code == 200
    assert 'data-testid="oidc-config-source">database<' in settings_page.text

    async_client.cookies.clear()
    login_page = await async_client.get("/auth/login")
    assert login_page.status_code == 200
    assert "/auth/redirect" not in login_page.text
    assert "/auth/login/admin" in login_page.text

    local_login = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert local_login.status_code == 303
    assert local_login.headers["location"] == "/"


@pytest.mark.asyncio
async def test_oidc_unlink_keeps_database_disabled_state(
    async_client, db, monkeypatch
) -> None:
    monkeypatch.setenv("OIDC_ISSUER", "https://legacy.example/realms/sokora")
    monkeypatch.setenv("OIDC_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv(
        "SOKORA_AUTH_CONFIG_ENCRYPTION_KEY",
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    )

    await _login_admin(async_client, monkeypatch)
    save = await async_client.post(
        "/auth/settings/oidc",
        data={
            "enabled": "true",
            "issuer": "https://db.example/realms/sokora",
            "client_id": "db-client",
            "client_secret": "db-secret",
            "scope": "openid profile email",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303

    unlink = await async_client.post(
        "/auth/settings/oidc/unlink",
        follow_redirects=False,
    )
    assert unlink.status_code == 303

    row = db.execute(
        text(
            "SELECT oidc_enabled, oidc_issuer, oidc_client_id, "
            "oidc_client_secret_encrypted FROM auth_config WHERE id = 1"
        )
    ).one()
    assert row.oidc_enabled in {0, False}
    assert row.oidc_issuer is None
    assert row.oidc_client_id is None
    assert row.oidc_client_secret_encrypted is None

    async_client.cookies.clear()
    login_page = await async_client.get("/auth/login")
    assert "/auth/redirect" not in login_page.text


def test_migration_adds_auth_config_without_replacing_existing_data(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    try:
        initialize_database(runtime)
        inspector = inspect(runtime.engine)
        assert "auth_config" in inspector.get_table_names()
        assert {
            "id",
            "oidc_enabled",
            "oidc_issuer",
            "oidc_client_id",
            "oidc_client_secret_encrypted",
            "oidc_scope",
        } == {
            column["name"] for column in inspector.get_columns("auth_config")
        }

        with runtime.session_factory() as db:
            assert db.scalar(text("SELECT COUNT(*) FROM groups")) > 0
            assert db.scalar(text("SELECT COUNT(*) FROM users")) > 0
    finally:
        runtime.dispose()
