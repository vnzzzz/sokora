"""認証経路の利用可否をruntime設定とshared DB設定から表現する。"""

from dataclasses import dataclass

from app.core.settings import AppSettings


@dataclass(frozen=True)
class AuthSettings:
    """1 requestで利用するimmutableな認証設定view。

    local admin/session設定はdeployment runtimeから取得する。OIDC設定はlegacy environment
    またはshared DB resolverのどちらかをsourceとし、oidc_sourceで判別できる。
    DB rowが存在する場合はoidc_enabled_overrideが明示enable/disableを保持し、disabled
    rowをlegacy environmentへfallbackさせない。
    """

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

    oidc_source: str = "legacy_environment"
    oidc_enabled_override: bool | None = None
    oidc_secret_configured: bool = False
    oidc_configuration_error: str | None = None

    @property
    def oidc_enabled(self) -> bool:
        """明示disabledを優先し、必要設定が揃った場合だけOIDCを有効とする。"""
        if self.oidc_enabled_override is False:
            return False
        return bool(
            self.oidc_issuer
            and self.oidc_client_id
            and self.oidc_client_secret
            and self.oidc_redirect_uri
        )

    @property
    def local_admin_enabled(self) -> bool:
        """明示flagとusername/passwordがすべて揃った場合だけlocal adminを有効にする。"""
        return self.local_auth_enabled and bool(
            self.local_admin_username and self.local_admin_password
        )

    @classmethod
    def from_app_settings(cls, settings: AppSettings) -> "AuthSettings":
        """deployment runtime設定をlegacy/environment認証viewへprojectする。"""
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
            oidc_source="legacy_environment",
            oidc_secret_configured=bool(settings.oidc_client_secret),
        )

    @classmethod
    def from_env(cls) -> "AuthSettings":
        """legacy/programmatic caller向けに現在environmentから認証設定を構築する。"""
        return cls.from_app_settings(AppSettings.from_env())
