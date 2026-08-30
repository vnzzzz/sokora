from app.core.settings import DEFAULT_DATABASE_URL, AppSettings


def test_app_settings_defaults_are_local_runtime_safe() -> None:
    settings = AppSettings.from_env({})

    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.log_level == "INFO"
    assert settings.auth_enabled is False
    assert settings.local_auth_enabled is True
    assert settings.session_ttl_seconds == 3600


def test_app_settings_can_be_built_from_explicit_mapping() -> None:
    settings = AppSettings.from_env(
        {
            "DATABASE_URL": "sqlite:////tmp/custom.db",
            "SOKORA_LOG_LEVEL": "debug",
            "SOKORA_AUTH_ENABLED": "true",
            "SOKORA_AUTH_SESSION_SECRET": "secret",
            "SOKORA_AUTH_SESSION_TTL_SECONDS": "7200",
            "SOKORA_LOCAL_AUTH_ENABLED": "false",
            "OIDC_ISSUER": "https://issuer.example",
            "OIDC_HTTP_TIMEOUT": "5.5",
        }
    )

    assert settings.database_url == "sqlite:////tmp/custom.db"
    assert settings.log_level == "DEBUG"
    assert settings.auth_enabled is True
    assert settings.session_secret == "secret"
    assert settings.session_ttl_seconds == 7200
    assert settings.local_auth_enabled is False
    assert settings.oidc_issuer == "https://issuer.example"
    assert settings.oidc_http_timeout == 5.5
