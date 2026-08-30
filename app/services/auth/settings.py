from dataclasses import dataclass
from os import environ
from pathlib import Path

from app.services.auth.state import AuthStateStore


def _get_bool(name: str, default: bool = False) -> bool:
    value = environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass
class AuthSettings:
    """認証関連の環境設定を保持するデータクラス"""

    auth_required: bool
    session_secret: str
    session_ttl_seconds: int

    oidc_issuer: str | None
    oidc_client_id: str | None
    oidc_client_secret: str | None
    oidc_redirect_uri: str | None
    oidc_scope: str
    oidc_http_timeout: float
    authorization_endpoint_override: str | None
    token_endpoint_override: str | None
    userinfo_endpoint_override: str | None
    logout_endpoint_override: str | None
    oidc_toggle_enabled: bool

    local_admin_username: str | None
    local_admin_password: str | None

    @property
    def oidc_enabled(self) -> bool:
        return all(
            [
                self.oidc_issuer,
                self.oidc_client_id,
                self.oidc_client_secret,
                self.oidc_redirect_uri,
            ]
        ) and self.oidc_toggle_enabled

    @property
    def local_admin_enabled(self) -> bool:
        return bool(self.local_admin_username and self.local_admin_password)

    @classmethod
    def from_env(cls) -> "AuthSettings":
        state_path = environ.get("SOKORA_AUTH_STATE_PATH")
        state_store = AuthStateStore(Path(state_path) if state_path else None)
        state = state_store.load_state()
        return cls(
            auth_required=_get_bool("SOKORA_AUTH_REQUIRED", default=False),
            session_secret=environ.get("SOKORA_AUTH_SESSION_SECRET", "dev-session-secret"),
            session_ttl_seconds=_get_int("SOKORA_AUTH_SESSION_TTL_SECONDS", default=3600),
            oidc_issuer=environ.get("OIDC_ISSUER"),
            oidc_client_id=environ.get("OIDC_CLIENT_ID"),
            oidc_client_secret=environ.get("OIDC_CLIENT_SECRET"),
            oidc_redirect_uri=environ.get("OIDC_REDIRECT_URL"),
            oidc_scope=environ.get("OIDC_SCOPES", "openid profile email"),
            oidc_http_timeout=_get_float("OIDC_HTTP_TIMEOUT", default=3.0),
            authorization_endpoint_override=environ.get("OIDC_AUTHORIZATION_ENDPOINT"),
            token_endpoint_override=environ.get("OIDC_TOKEN_ENDPOINT"),
            userinfo_endpoint_override=environ.get("OIDC_USERINFO_ENDPOINT"),
            logout_endpoint_override=environ.get("OIDC_LOGOUT_ENDPOINT"),
            oidc_toggle_enabled=state.oidc_enabled,
            local_admin_username=environ.get("SOKORA_LOCAL_ADMIN_USERNAME"),
            local_admin_password=environ.get("SOKORA_LOCAL_ADMIN_PASSWORD"),
        )
