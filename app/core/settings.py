"""application runtime設定の読み取りとsecurity validationを集約する。

environment parsingをこのmoduleへ閉じ込め、router/serviceが``os.environ``を直接参照しない
ようにする。各 :class:`AppSettings` instanceは生成時点のsourceをimmutableに保持するが、
application全体で同じinstanceを再利用するか、providerが新しいinstanceを作るかはcallerが
決める。``validate_runtime()`` が検証するのも呼び出したinstanceだけである。
"""

from dataclasses import dataclass
from os import environ
from typing import Mapping

DEFAULT_DATABASE_URL = "sqlite:///data/sokora.db"
# Local development用の既定値。認証guardを有効にするruntimeではvalidate_runtime()が
# この値を拒否し、明示的なsecret injectionを必須にする。
DEFAULT_SESSION_SECRET = "dev-session-secret"


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
    """1回のsettings readから構築したimmutableなapplication設定instance。

    ``from_env()`` で生成した場合、このinstanceはその呼び出し時点のprocess environmentを
    保持する。後続の``from_env()`` が同じ値を返すことや、applicationがこのinstanceだけを
    lifetime全体で再利用することまでは保証しない。

    default値はlocal developmentを成立させるための値を含む。``from_env()`` やconstructorは
    security validationを自動実行しないため、検証が必要なboundaryのcallerが対象instanceへ
    :meth:`validate_runtime` を明示的に適用する。application factory/lifespanが検証した
    instanceとは別に後から生成されたinstanceまで、自動的にvalidated扱いにはならない。

    OIDCやlocal adminの「利用可能か」という派生判定はauth layerが所有し、この型はprovider
    固有endpointやprocess-local mutable stateを持たない。
    """

    app_version: str = "1.0.0"
    log_level: str = "INFO"
    database_url: str = DEFAULT_DATABASE_URL

    auth_enabled: bool = False
    session_secret: str = DEFAULT_SESSION_SECRET
    session_ttl_seconds: int = 3600
    session_https_only: bool = False
    local_auth_enabled: bool = True

    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_scope: str = "openid profile email"
    oidc_http_timeout: float = 3.0

    local_admin_username: str | None = None
    local_admin_password: str | None = None

    def validate_runtime(self) -> None:
        """startup前にsecurity contractを弱める設定組合せを拒否する。

        認証guardを有効にした場合、signed sessionはauthorization境界の一部になるため、
        空secretやrepository既定のdevelopment secretを許可しない。認証を無効にした
        development runtimeまで同じsecret要件で起動不能にはしない。

        OIDC/local admin credentialの完全性は、それぞれの経路を「利用可能」と判定する
        auth settings側で扱う。
        """
        normalized_secret = self.session_secret.strip()
        if self.auth_enabled and (
            not normalized_secret or normalized_secret == DEFAULT_SESSION_SECRET
        ):
            raise ValueError(
                "SOKORA_AUTH_SESSION_SECRET must be explicitly configured "
                "when SOKORA_AUTH_ENABLED=true"
            )

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> "AppSettings":
        """明示mappingまたはprocess environmentから1回分の設定snapshotを構築する。

        ``values`` を渡せるのはtestやprogrammatic callerがprocess-global environmentへ
        依存せず同じparserを利用するためである。このmethodは設定変更を監視せず、返却後に
        source mappingが変わっても既存instanceへ反映しない。
        """
        source = environ if values is None else values
        return cls(
            log_level=source.get("SOKORA_LOG_LEVEL", "INFO").upper(),
            database_url=source.get("DATABASE_URL", DEFAULT_DATABASE_URL),
            auth_enabled=_get_bool(source, "SOKORA_AUTH_ENABLED", False),
            session_secret=source.get(
                "SOKORA_AUTH_SESSION_SECRET", DEFAULT_SESSION_SECRET
            ),
            session_ttl_seconds=_get_int(
                source, "SOKORA_AUTH_SESSION_TTL_SECONDS", 3600
            ),
            session_https_only=_get_bool(
                source, "SOKORA_AUTH_SESSION_HTTPS_ONLY", False
            ),
            local_auth_enabled=_get_bool(source, "SOKORA_LOCAL_AUTH_ENABLED", True),
            oidc_issuer=source.get("OIDC_ISSUER"),
            oidc_client_id=source.get("OIDC_CLIENT_ID"),
            oidc_client_secret=source.get("OIDC_CLIENT_SECRET"),
            oidc_redirect_uri=source.get("OIDC_REDIRECT_URL"),
            oidc_scope=source.get("OIDC_SCOPES", "openid profile email"),
            oidc_http_timeout=_get_float(source, "OIDC_HTTP_TIMEOUT", 3.0),
            local_admin_username=source.get("SOKORA_LOCAL_ADMIN_USERNAME"),
            local_admin_password=source.get("SOKORA_LOCAL_ADMIN_PASSWORD"),
        )
