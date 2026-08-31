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
    """Return the OpenID Provider Configuration URL for an issuer."""
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


class OIDCClient:
    """Wrap Authlib's Starlette OIDC integration behind a small application API."""

    def __init__(self, settings: AuthSettings, client: Any | None = None) -> None:
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
        """Create an authorization URL through provider discovery.

        Authlib generates and persists the OAuth state and OIDC nonce in the
        signed Starlette session. The callback consumes that temporary state.
        """
        try:
            response = await self._client.authorize_redirect(
                request,
                redirect_uri or self.settings.oidc_redirect_uri,
            )
        except Exception as exc:
            raise OIDCError(f"OIDC authorization discovery failed: {exc}") from exc
        return response.headers["location"]

    async def exchange_code(self, *, request: Request) -> OIDCLoginResult:
        """Exchange a code and return identity claims validated by Authlib.

        Authlib validates callback state and the ID token's nonce, issuer,
        audience, signature, and time-based claims using discovery metadata and
        JWKS before exposing ``userinfo``.
        """
        try:
            token = await self._client.authorize_access_token(request)
        except MismatchingStateError as exc:
            raise OIDCStateError("OIDC state validation failed") from exc
        except OAuthError as exc:
            raise OIDCError(f"OIDC token exchange failed: {exc}") from exc
        except Exception as exc:
            raise OIDCError(f"OIDC token validation failed: {exc}") from exc

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
        """Return an RP-Initiated Logout URL discovered from provider metadata.

        The persistent application session does not retain an ID token. The
        standards-defined ``client_id`` parameter therefore identifies the RP
        when requesting a registered post-logout redirect URI.
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
            raise OIDCError(f"OIDC logout discovery failed: {exc}") from exc
        except Exception as exc:
            raise OIDCError(f"OIDC logout failed: {exc}") from exc
        return response.headers["location"]

    async def validate_logout_response(self, request: Request) -> None:
        """Validate RP-Initiated Logout state returned by the provider."""
        try:
            await self._client.validate_logout_response(request)
        except OAuthError as exc:
            raise OIDCStateError("OIDC logout state validation failed") from exc
        except Exception as exc:
            raise OIDCError(f"OIDC logout callback failed: {exc}") from exc
