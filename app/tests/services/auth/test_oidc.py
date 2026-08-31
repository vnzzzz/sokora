from typing import Any

import pytest
from authlib.integrations.base_client.errors import MismatchingStateError
from starlette.responses import RedirectResponse

from app.core.settings import AppSettings
from app.services.auth.oidc import OIDCClient, OIDCError, OIDCStateError
from app.services.auth.settings import AuthSettings


def _settings() -> AuthSettings:
    return AuthSettings.from_app_settings(
        AppSettings(
            oidc_issuer="https://idp.example/realms/sokora",
            oidc_client_id="sokora-web",
            oidc_client_secret="secret",
            oidc_redirect_uri="https://sokora.example/auth/callback",
        )
    )


class FakeAuthlibClient:
    def __init__(self, token: dict[str, Any] | None = None) -> None:
        self.token = token or {
            "userinfo": {"sub": "user-123", "preferred_username": "alice"}
        }

    async def authorize_redirect(self, request, redirect_uri):
        del request, redirect_uri
        return RedirectResponse("https://idp.example/authorize?state=state")

    async def authorize_access_token(self, request):
        del request
        return self.token

    async def logout_redirect(
        self, request, post_logout_redirect_uri=None, client_id=None
    ):
        del request, post_logout_redirect_uri, client_id
        return RedirectResponse("https://idp.example/logout?state=logout-state")

    async def validate_logout_response(self, request):
        del request
        return {
            "post_logout_redirect_uri": "https://sokora.example/auth/logout/callback"
        }


@pytest.mark.asyncio
async def test_oidc_client_projects_validated_userinfo() -> None:
    client = OIDCClient(_settings(), client=FakeAuthlibClient())

    result = await client.exchange_code(request=object())  # type: ignore[arg-type]

    assert result.subject == "user-123"
    assert result.username == "alice"


@pytest.mark.asyncio
async def test_oidc_client_rejects_token_without_validated_userinfo() -> None:
    client = OIDCClient(
        _settings(), client=FakeAuthlibClient(token={"access_token": "x"})
    )

    with pytest.raises(OIDCError, match="validated ID token"):
        await client.exchange_code(request=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_oidc_client_maps_authlib_state_mismatch() -> None:
    class StateMismatchClient(FakeAuthlibClient):
        async def authorize_access_token(self, request):
            del request
            raise MismatchingStateError()

    client = OIDCClient(_settings(), client=StateMismatchClient())

    with pytest.raises(OIDCStateError, match="state validation"):
        await client.exchange_code(request=object())  # type: ignore[arg-type]
