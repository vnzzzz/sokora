"""Application settings loaded from environment variables.

Environment parsing is centralized here so application/runtime components can
receive an explicit settings object instead of reading ``os.environ`` directly.
"""

from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Mapping

DEFAULT_DATABASE_URL = "sqlite:///data/sokora.db"


def _get_bool(values: Mapping[str, str], name: str, default: bool) -> bool:
    value = values.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(values: Mapping[str, str], name: str, default: int) -> int:
    value = values.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(values: Mapping[str, str], name: str, default: float) -> float:
    value = values.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppSettings:
    """Static application settings derived from environment variables."""

    app_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = DEFAULT_DATABASE_URL

    auth_enabled: bool = False
    session_secret: str = "dev-session-secret"
    session_ttl_seconds: int = 3600
    local_auth_enabled: bool = True
    auth_state_path: Path | None = None

    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_scope: str = "openid profile email"
    oidc_http_timeout: float = 3.0
    authorization_endpoint_override: str | None = None
    token_endpoint_override: str | None = None
    userinfo_endpoint_override: str | None = None
    logout_endpoint_override: str | None = None

    local_admin_username: str | None = None
    local_admin_password: str | None = None

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> "AppSettings":
        """Build settings from an explicit mapping or the process environment."""
        source = environ if values is None else values
        state_path = source.get("SOKORA_AUTH_STATE_PATH")
        return cls(
            log_level=source.get("SOKORA_LOG_LEVEL", "INFO").upper(),
            database_url=source.get("DATABASE_URL", DEFAULT_DATABASE_URL),
            auth_enabled=_get_bool(source, "SOKORA_AUTH_ENABLED", False),
            session_secret=source.get(
                "SOKORA_AUTH_SESSION_SECRET", "dev-session-secret"
            ),
            session_ttl_seconds=_get_int(
                source, "SOKORA_AUTH_SESSION_TTL_SECONDS", 3600
            ),
            local_auth_enabled=_get_bool(source, "SOKORA_LOCAL_AUTH_ENABLED", True),
            auth_state_path=Path(state_path) if state_path else None,
            oidc_issuer=source.get("OIDC_ISSUER"),
            oidc_client_id=source.get("OIDC_CLIENT_ID"),
            oidc_client_secret=source.get("OIDC_CLIENT_SECRET"),
            oidc_redirect_uri=source.get("OIDC_REDIRECT_URL"),
            oidc_scope=source.get("OIDC_SCOPES", "openid profile email"),
            oidc_http_timeout=_get_float(source, "OIDC_HTTP_TIMEOUT", 3.0),
            authorization_endpoint_override=source.get(
                "OIDC_AUTHORIZATION_ENDPOINT"
            ),
            token_endpoint_override=source.get("OIDC_TOKEN_ENDPOINT"),
            userinfo_endpoint_override=source.get("OIDC_USERINFO_ENDPOINT"),
            logout_endpoint_override=source.get("OIDC_LOGOUT_ENDPOINT"),
            local_admin_username=source.get("SOKORA_LOCAL_ADMIN_USERNAME"),
            local_admin_password=source.get("SOKORA_LOCAL_ADMIN_PASSWORD"),
        )
