import httpx
import pytest

from app.core.settings import AppSettings
from app.services.auth.config_store import (
    AuthConfigValidationError,
    OIDCDiscoveryError,
    check_oidc_discovery,
    resolve_auth_settings,
    save_oidc_config,
)


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


def test_oidc_client_secret_is_preserved_as_opaque_value(db) -> None:
    secret = "  opaque-client-secret\t"
    settings = AppSettings(
        oidc_redirect_uri="https://sokora.example/auth/callback",
        auth_config_encryption_key=("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
    )

    save_oidc_config(
        db,
        settings,
        enabled=True,
        issuer="https://idp.example/realms/sokora",
        client_id="sokora-web",
        client_secret=secret,
        scope="openid profile email",
    )

    resolved = resolve_auth_settings(db, settings)
    assert resolved.oidc_client_secret == secret


def test_first_db_save_can_encrypt_matching_legacy_secret(db) -> None:
    settings = AppSettings(
        oidc_issuer="https://legacy.example/realms/sokora",
        oidc_client_id="legacy-client",
        oidc_client_secret="legacy-secret",
        oidc_redirect_uri="https://sokora.example/auth/callback",
        auth_config_encryption_key=("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
    )

    save_oidc_config(
        db,
        settings,
        enabled=True,
        issuer="https://legacy.example/realms/sokora",
        client_id="legacy-client",
        client_secret="",
        scope="openid profile email",
    )

    resolved = resolve_auth_settings(db, settings)
    assert resolved.oidc_source == "database"
    assert resolved.oidc_client_secret == "legacy-secret"


def test_first_db_save_requires_secret_when_client_identity_changes(db) -> None:
    settings = AppSettings(
        oidc_issuer="https://legacy.example/realms/sokora",
        oidc_client_id="legacy-client",
        oidc_client_secret="legacy-secret",
        oidc_redirect_uri="https://sokora.example/auth/callback",
        auth_config_encryption_key=(
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        ),
    )

    with pytest.raises(AuthConfigValidationError, match="client secret"):
        save_oidc_config(
            db,
            settings,
            enabled=True,
            issuer="https://new.example/realms/sokora",
            client_id="new-client",
            client_secret="",
            scope="openid profile email",
        )


def test_db_client_identity_change_requires_new_secret(db) -> None:
    settings = AppSettings(
        oidc_redirect_uri="https://sokora.example/auth/callback",
        auth_config_encryption_key=(
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        ),
    )
    save_oidc_config(
        db,
        settings,
        enabled=True,
        issuer="https://idp.example/realms/sokora",
        client_id="client-a",
        client_secret="secret-a",
        scope="openid profile email",
    )

    with pytest.raises(AuthConfigValidationError, match="client secret"):
        save_oidc_config(
            db,
            settings,
            enabled=True,
            issuer="https://idp.example/realms/other",
            client_id="client-b",
            client_secret="",
            scope="openid profile email",
        )
