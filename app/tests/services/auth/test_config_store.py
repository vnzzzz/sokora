import httpx
import pytest

from app.services.auth.config_store import OIDCDiscoveryError, check_oidc_discovery


@pytest.mark.asyncio
async def test_oidc_discovery_uses_standard_well_known_metadata() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "issuer": "https://idp.example/realms/sokora",
                "authorization_endpoint": "https://idp.example/auth",
                "token_endpoint": "https://idp.example/token",
                "jwks_uri": "https://idp.example/jwks",
            },
        )

    metadata = await check_oidc_discovery(
        "https://idp.example/realms/sokora/",
        1.0,
        transport=httpx.MockTransport(handler),
    )

    assert seen_urls == [
        "https://idp.example/realms/sokora/.well-known/openid-configuration"
    ]
    assert metadata["issuer"] == "https://idp.example/realms/sokora"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, text="unavailable"),
        httpx.Response(200, json={"issuer": "https://idp.example"}),
    ],
)
async def test_oidc_discovery_rejects_unavailable_or_incomplete_metadata(
    response: httpx.Response,
) -> None:
    transport = httpx.MockTransport(lambda _request: response)

    with pytest.raises(OIDCDiscoveryError):
        await check_oidc_discovery(
            "https://idp.example/realms/sokora",
            1.0,
            transport=transport,
        )
