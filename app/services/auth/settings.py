"""認証経路の利用可否をshared application settingsから導出する。"""

from dataclasses import dataclass

from app.core.settings import AppSettings


@dataclass(frozen=True)
class AuthSettings:
    """shared runtime settingsから導出するimmutableな認証設定view。

    OIDC/local adminの利用可否はruntime設定の組合せから都度決定し、replica-local fileや
    runtime toggleをSSoTにしない。複数replicaでは同じsecret/configを注入することで、
    どのreplicaでも同じsessionと認証経路を解釈できることを前提とする。
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

    @property
    def oidc_enabled(self) -> bool:
        """OIDC authorization code flowに必要な4設定がすべて揃った場合だけ有効とする。

        issuer/client ID/client secret/redirect URIの一部だけが設定された状態を「部分的に
        利用可能」とは扱わず、login UIとOIDC必須dependencyは同じ判定を利用する。
        """
        return bool(
            self.oidc_issuer
            and self.oidc_client_id
            and self.oidc_client_secret
            and self.oidc_redirect_uri
        )

    @property
    def local_admin_enabled(self) -> bool:
        """明示flagとusername/passwordがすべて揃った場合だけlocal adminを有効にする。

        flagの既定値がtrueでもcredential不足ならlogin経路は利用不可とする。これにより、
        credential未設定を空文字credentialとして解釈することを避ける。
        """
        return self.local_auth_enabled and bool(
            self.local_admin_username and self.local_admin_password
        )

    @classmethod
    def from_app_settings(cls, settings: AppSettings) -> "AuthSettings":
        """application設定snapshotを認証layerの必要項目だけへprojectする。

        値をcopyするだけで、OIDC discovery結果やlogin状態などrequest/processごとのmutable
        stateはこの設定objectへ保持しない。
        """
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
        """legacy/programmatic caller向けに現在environmentから認証設定を構築する。

        environment parsing自体は :class:`AppSettings` に集約したままとし、このcompatibility
        helperへ認証専用の別parserを増やさない。application request pathではshared settings
        providerから :meth:`from_app_settings` を使う。
        """
        return cls.from_app_settings(AppSettings.from_env())
