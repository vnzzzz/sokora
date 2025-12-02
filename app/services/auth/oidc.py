import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.auth.settings import AuthSettings

logger = logging.getLogger(__name__)


class OIDCError(Exception):
    """OIDC フロー中のエラーを示す例外"""


@dataclass
class OIDCLoginResult:
    """OIDC ログイン完了時の結果"""

    subject: str
    username: str
    id_token: str
    access_token: str
    refresh_token: str | None = None


class OIDCClient:
    """Keycloak OIDC と対話するクライアント"""

    def __init__(self, settings: AuthSettings, http_client: httpx.Client | None = None) -> None:
        if not settings.oidc_enabled:
            raise OIDCError("OIDC settings are incomplete")
        self.settings = settings
        timeout = settings.oidc_http_timeout
        self.http_client = http_client or httpx.Client(timeout=timeout)

    def build_authorization_url(self, state: str, nonce: str) -> str:
        endpoint = self._authorization_endpoint()
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.oidc_client_id or "",
                "redirect_uri": self.settings.oidc_redirect_uri or "",
                "scope": self.settings.oidc_scope,
                "state": state,
                "nonce": nonce,
            }
        )
        return f"{endpoint}?{query}"

    def exchange_code(
        self,
        code: str,
        state: str,
        nonce: str,
        redirect_uri: str | None = None,
    ) -> OIDCLoginResult:
        token_url = self._token_endpoint()
        callback_uri = redirect_uri or self.settings.oidc_redirect_uri or ""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.settings.oidc_client_id or "",
            "client_secret": self.settings.oidc_client_secret or "",
            "code": code,
            "redirect_uri": callback_uri,
        }
        try:
            token_resp = self.http_client.post(token_url, data=data)
            token_resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to exchange code with Keycloak: %s", exc)
            raise OIDCError("Failed to exchange authorization code") from exc

        token_payload = token_resp.json()
        access_token = token_payload.get("access_token")
        id_token = token_payload.get("id_token")
        refresh_token = token_payload.get("refresh_token")
        if not access_token or not id_token:
            raise OIDCError("Token response missing access_token or id_token")

        subject, username = self._fetch_userinfo(access_token)
        return OIDCLoginResult(
            subject=subject,
            username=username,
            id_token=id_token,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def get_logout_url(self, id_token_hint: str, post_logout_redirect_uri: str) -> str | None:
        endpoint = self._logout_endpoint()
        if endpoint is None:
            return None
        query = urllib.parse.urlencode(
            {
                "id_token_hint": id_token_hint,
                "post_logout_redirect_uri": post_logout_redirect_uri,
            }
        )
        return f"{endpoint}?{query}"

    def _authorization_endpoint(self) -> str:
        if self.settings.authorization_endpoint_override:
            return self.settings.authorization_endpoint_override
        issuer = self.settings.oidc_issuer or ""
        return f"{issuer}/protocol/openid-connect/auth"

    def _token_endpoint(self) -> str:
        if self.settings.token_endpoint_override:
            return self.settings.token_endpoint_override
        issuer = self.settings.oidc_issuer or ""
        return f"{issuer}/protocol/openid-connect/token"

    def _userinfo_endpoint(self) -> str:
        if self.settings.userinfo_endpoint_override:
            return self.settings.userinfo_endpoint_override
        issuer = self.settings.oidc_issuer or ""
        return f"{issuer}/protocol/openid-connect/userinfo"

    def _logout_endpoint(self) -> str | None:
        if self.settings.logout_endpoint_override:
            return self.settings.logout_endpoint_override
        if not self.settings.oidc_issuer:
            return None
        return f"{self.settings.oidc_issuer}/protocol/openid-connect/logout"

    def _fetch_userinfo(self, access_token: str) -> tuple[str, str]:
        userinfo_url = self._userinfo_endpoint()
        try:
            resp = self.http_client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch userinfo: %s", exc)
            raise OIDCError("Failed to fetch userinfo") from exc

        data: dict[str, Any] = resp.json()
        subject = data.get("sub")
        if not subject:
            raise OIDCError("Userinfo response missing sub")
        username = data.get("preferred_username") or subject
        return subject, username
