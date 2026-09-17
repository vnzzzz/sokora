"""Standards-based OpenID Connect client boundary."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from authlib.integrations.base_client.errors import (  # type: ignore[import-untyped]
    MismatchingStateError,
    OAuthError,
)
from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from starlette.requests import Request

from app.services.auth.settings import AuthSettings


class OIDCError(RuntimeError):
    """OIDC discovery, token exchange, validation, or logout failure."""


class OIDCStateError(OIDCError):
    """OIDC state validation failure."""


@dataclass(frozen=True)
class OIDCLoginResult:
    """Validated identity projected from an OIDC ID token."""

    subject: str
    username: str


def oidc_discovery_url(issuer: str) -> str:
    """issuerからOpenID Provider Configuration URLを組み立てる。

    Args:
        issuer: provider issuer URL。

    Returns:
        trailing slashを正規化したstandard discovery URL。
    """
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


class OIDCClient:
    """Wrap Authlib's Starlette OIDC integration behind a small application API."""

    def __init__(self, settings: AuthSettings, client: Any | None = None) -> None:
        """effective settingsからOIDC client boundaryを初期化する。

        Args:
            settings: request時点で解決済みのauthentication settings。
            client: test等で注入するAuthlib-compatible client。

        Raises:
            OIDCError: OIDCが有効な設定として成立していない場合。
        """
        if not settings.oidc_enabled:
            raise OIDCError("OIDC is not configured")
        self.settings = settings
        if client is not None:
            self._client = client
            return

        oauth = OAuth()
        self._client = oauth.register(
            name="oidc",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            server_metadata_url=oidc_discovery_url(str(settings.oidc_issuer)),
            client_kwargs={
                "scope": settings.oidc_scope,
                "timeout": settings.oidc_http_timeout,
            },
        )

    async def build_authorization_url(
        self,
        *,
        request: Request,
        redirect_uri: str | None = None,
    ) -> str:
        """provider discoveryを使ってauthorization URLを生成する。

        AuthlibがOAuth stateとOIDC nonceをsigned Starlette sessionへ保存し、callbackで消費する。

        Args:
            request: state/nonceを保存するStarlette request。
            redirect_uri: callback URI override。未指定時はsettings値を使う。

        Returns:
            provider authorization endpointへのredirect URL。

        Raises:
            OIDCError: discoveryまたはauthorization redirect生成に失敗した場合。
        """
        try:
            response = await self._client.authorize_redirect(
                request,
                redirect_uri or self.settings.oidc_redirect_uri,
            )
        except Exception as exc:
            raise OIDCError("OIDC authorization discovery failed") from exc
        return response.headers["location"]

    async def exchange_code(self, *, request: Request) -> OIDCLoginResult:
        """authorization codeを交換し、検証済みidentityを返す。

        Authlibがcallback stateとID tokenのnonce、issuer、audience、signature、time-based claimsを
        discovery metadata/JWKSで検証してから``userinfo``を公開する。

        Args:
            request: provider callback queryとtemporary session stateを持つrequest。

        Returns:
            validated subjectと表示用username。

        Raises:
            OIDCStateError: callback state mismatchの場合。
            OIDCError: token exchange、ID token validation、required claim取得に失敗した場合。
        """
        try:
            token = await self._client.authorize_access_token(request)
        except MismatchingStateError as exc:
            raise OIDCStateError("OIDC state validation failed") from exc
        except OAuthError as exc:
            raise OIDCError("OIDC token exchange failed") from exc
        except Exception as exc:
            raise OIDCError("OIDC token validation failed") from exc

        userinfo = token.get("userinfo")
        if not isinstance(userinfo, Mapping):
            raise OIDCError("OIDC provider did not return a validated ID token")
        subject = userinfo.get("sub")
        if not isinstance(subject, str) or not subject:
            raise OIDCError("OIDC ID token is missing sub")
        username = (
            userinfo.get("preferred_username")
            or userinfo.get("email")
            or userinfo.get("name")
            or subject
        )
        return OIDCLoginResult(subject=subject, username=str(username))

    async def get_logout_url(
        self,
        *,
        request: Request,
        post_logout_redirect_uri: str,
    ) -> str | None:
        """provider metadataからRP-Initiated Logout URLを取得する。

        persistent application sessionにはID tokenを保持しないため、registered post-logout redirect
        URIを要求する際はstandards-defined ``client_id`` でRPを識別する。

        Args:
            request: logout stateを一時保存するrequest。
            post_logout_redirect_uri: provider logout後のregistered callback URI。

        Returns:
            provider logout URL。providerが``end_session_endpoint``を持たなければ ``None``。

        Raises:
            OIDCError: metadata取得またはlogout redirect生成に失敗した場合。
        """
        try:
            response = await self._client.logout_redirect(
                request,
                post_logout_redirect_uri=post_logout_redirect_uri,
                client_id=self.settings.oidc_client_id,
            )
        except RuntimeError as exc:
            if "end_session_endpoint" in str(exc):
                return None
            raise OIDCError("OIDC logout discovery failed") from exc
        except Exception as exc:
            raise OIDCError("OIDC logout failed") from exc
        return response.headers["location"]

    async def validate_logout_response(self, request: Request) -> None:
        """providerから返されたRP-Initiated Logout stateを検証する。

        Args:
            request: logout callback queryとtemporary stateを持つrequest。

        Raises:
            OIDCStateError: logout state validationに失敗した場合。
            OIDCError: その他のlogout callback validationに失敗した場合。
        """
        try:
            await self._client.validate_logout_response(request)
        except OAuthError as exc:
            raise OIDCStateError("OIDC logout state validation failed") from exc
        except Exception as exc:
            raise OIDCError("OIDC logout callback failed") from exc
