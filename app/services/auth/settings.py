from dataclasses import dataclass

from app.core.settings import AppSettings
from app.services.auth.state import AuthStateStore


@dataclass
class AuthSettings:
    """Authentication settings including the runtime OIDC toggle state."""

    auth_enabled: bool
    session_secret: str
    session_ttl_seconds: int
    local_auth_enabled: bool

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
        return (
            all(
                [
                    self.oidc_issuer,
                    self.oidc_client_id,
                    self.oidc_client_secret,
                    self.oidc_redirect_uri,
                ]
            )
            and self.oidc_toggle_enabled
        )

    @property
    def local_admin_enabled(self) -> bool:
        return self.local_auth_enabled and bool(
            self.local_admin_username and self.local_admin_password
        )

    @classmethod
    def from_app_settings(cls, settings: AppSettings) -> "AuthSettings":
        """Combine static application settings with mutable auth state."""
        state_store = AuthStateStore(settings.auth_state_path)
        state = state_store.load_state()
        return cls(
            auth_enabled=settings.auth_enabled,
            session_secret=settings.session_secret,
            session_ttl_seconds=settings.session_ttl_seconds,
            local_auth_enabled=settings.local_auth_enabled,
            oidc_issuer=settings.oidc_issuer,
            oidc_client_id=settings.oidc_client_id,
            oidc_client_secret=settings.oidc_client_secret,
            oidc_redirect_uri=settings.oidc_redirect_uri,
            oidc_scope=settings.oidc_scope,
            oidc_http_timeout=settings.oidc_http_timeout,
            authorization_endpoint_override=settings.authorization_endpoint_override,
            token_endpoint_override=settings.token_endpoint_override,
            userinfo_endpoint_override=settings.userinfo_endpoint_override,
            logout_endpoint_override=settings.logout_endpoint_override,
            oidc_toggle_enabled=state.oidc_enabled,
            local_admin_username=settings.local_admin_username,
            local_admin_password=settings.local_admin_password,
        )

    @classmethod
    def from_env(cls) -> "AuthSettings":
        """Compatibility helper; environment parsing remains centralized."""
        return cls.from_app_settings(AppSettings.from_env())
