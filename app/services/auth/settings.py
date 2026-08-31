from dataclasses import dataclass

from app.core.settings import AppSettings


@dataclass(frozen=True)
class AuthSettings:
    """Authentication configuration derived only from shared runtime settings."""

    auth_enabled: bool
    session_secret: str
    session_ttl_seconds: int
    session_https_only: bool
    local_auth_enabled: bool

    oidc_issuer: str | None
    oidc_client_id: str | None
    oidc_client_secret: str | None
    oidc_redirect_uri: str | None
    oidc_scope: str
    oidc_http_timeout: float

    local_admin_username: str | None
    local_admin_password: str | None

    @property
    def oidc_enabled(self) -> bool:
        """OIDC is enabled when all mandatory provider settings are present."""
        return bool(
            self.oidc_issuer
            and self.oidc_client_id
            and self.oidc_client_secret
            and self.oidc_redirect_uri
        )

    @property
    def local_admin_enabled(self) -> bool:
        return self.local_auth_enabled and bool(
            self.local_admin_username and self.local_admin_password
        )

    @classmethod
    def from_app_settings(cls, settings: AppSettings) -> "AuthSettings":
        """Build auth settings without process-local mutable state."""
        return cls(
            auth_enabled=settings.auth_enabled,
            session_secret=settings.session_secret,
            session_ttl_seconds=settings.session_ttl_seconds,
            session_https_only=settings.session_https_only,
            local_auth_enabled=settings.local_auth_enabled,
            oidc_issuer=settings.oidc_issuer,
            oidc_client_id=settings.oidc_client_id,
            oidc_client_secret=settings.oidc_client_secret,
            oidc_redirect_uri=settings.oidc_redirect_uri,
            oidc_scope=settings.oidc_scope,
            oidc_http_timeout=settings.oidc_http_timeout,
            local_admin_username=settings.local_admin_username,
            local_admin_password=settings.local_admin_password,
        )

    @classmethod
    def from_env(cls) -> "AuthSettings":
        """Compatibility helper; environment parsing remains centralized."""
        return cls.from_app_settings(AppSettings.from_env())
