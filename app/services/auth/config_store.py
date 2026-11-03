"""Shared DB-backed OIDC configuration, encryption, and discovery checks."""

from dataclasses import replace
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.settings import AppSettings
from app.models.auth_config import AuthConfig
from app.services.auth.oidc import oidc_discovery_url
from app.services.auth.settings import AuthSettings
from app.services.transaction import transaction

AUTH_CONFIG_ID = 1
DEFAULT_OIDC_SCOPE = "openid profile email"


class AuthConfigError(RuntimeError):
    """Base error for editable authentication configuration."""


class AuthConfigValidationError(AuthConfigError):
    """Administrator-supplied OIDC configuration is incomplete or invalid."""


class OIDCDiscoveryError(AuthConfigError):
    """OIDC discovery metadata could not be retrieved or validated."""


def get_auth_config(db: Session) -> AuthConfig | None:
    """singleton authentication config rowを取得する。

    Args:
        db: authentication configを読むDB session。

    Returns:
        保存済みconfig。未作成なら ``None``。
    """
    return db.get(AuthConfig, AUTH_CONFIG_ID)


def _fernet(encryption_key: str | None) -> Fernet:
    """runtime keyからFernet instanceを構築する。

    Args:
        encryption_key: deploymentから渡されるFernet key。

    Returns:
        client secret暗号化/復号に使うFernet instance。

    Raises:
        AuthConfigValidationError: keyが未設定またはFernet keyとして不正な場合。
    """
    if not encryption_key:
        raise AuthConfigValidationError("OIDC設定暗号鍵がruntimeに設定されていません。")
    try:
        return Fernet(encryption_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise AuthConfigValidationError("OIDC設定暗号鍵の形式が不正です。") from exc


def encrypt_client_secret(secret: str, encryption_key: str | None) -> str:
    """OIDC client secretを保存用ciphertextへ暗号化する。

    Args:
        secret: 平文client secret。
        encryption_key: deployment提供のFernet key。

    Returns:
        ASCII表現のFernet ciphertext。

    Raises:
        AuthConfigValidationError: encryption keyが未設定または不正な場合。
    """
    return _fernet(encryption_key).encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_client_secret(ciphertext: str, encryption_key: str | None) -> str:
    """保存済みOIDC client secretを復号する。

    Args:
        ciphertext: 保存済みFernet ciphertext。
        encryption_key: deployment提供のFernet key。

    Returns:
        UTF-8 client secret。

    Raises:
        AuthConfigValidationError: key不整合、ciphertext破損、decode failureの場合。
    """
    try:
        plaintext = _fernet(encryption_key).decrypt(ciphertext.encode("ascii"))
    except (InvalidToken, UnicodeError) as exc:
        raise AuthConfigValidationError(
            "OIDC client secretを復号できません。暗号鍵または保存値を確認してください。"
        ) from exc
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuthConfigValidationError(
            "OIDC client secretを復号できません。暗号鍵または保存値を確認してください。"
        ) from exc


def resolve_auth_settings(db: Session, app_settings: AppSettings) -> AuthSettings:
    """request時点のeffective authentication settingsを解決する。

    DB rowが無い場合だけlegacy environment設定を使う。singleton rowが存在した時点でDBを
    authoritative sourceとし、明示disabled rowからenvironment値へfallbackしない。

    Args:
        db: shared auth configを読むDB session。
        app_settings: process起動時のenvironment由来application settings。

    Returns:
        DB/environment precedenceとsecret復号結果を反映したeffective settings。
    """
    legacy = AuthSettings.from_app_settings(app_settings)
    config = get_auth_config(db)
    if config is None:
        return legacy

    encrypted_secret = (
        str(config.oidc_client_secret_encrypted)
        if config.oidc_client_secret_encrypted
        else None
    )
    secret: str | None = None
    configuration_error: str | None = None

    if bool(config.oidc_enabled):
        if encrypted_secret is None:
            configuration_error = "OIDC client secretが設定されていません。"
        else:
            try:
                secret = decrypt_client_secret(
                    encrypted_secret,
                    app_settings.auth_config_encryption_key,
                )
            except AuthConfigValidationError as exc:
                configuration_error = str(exc)

    return replace(
        legacy,
        oidc_issuer=str(config.oidc_issuer) if config.oidc_issuer else None,
        oidc_client_id=str(config.oidc_client_id) if config.oidc_client_id else None,
        oidc_client_secret=secret,
        oidc_scope=str(config.oidc_scope or DEFAULT_OIDC_SCOPE),
        oidc_source="database",
        oidc_enabled_override=bool(config.oidc_enabled),
        oidc_secret_configured=encrypted_secret is not None,
        oidc_configuration_error=configuration_error,
    )


def validate_oidc_scope_for_enable(scope: str) -> str:
    """OIDC有効化に必要なscopeを正規化・検証する。

    Args:
        scope: 管理画面から入力されたspace-separated scope。

    Returns:
        空値をdefaultへ補正したscope。

    Raises:
        AuthConfigValidationError: ``openid`` scopeが含まれない場合。
    """
    normalized_scope = scope.strip() or DEFAULT_OIDC_SCOPE
    if "openid" not in normalized_scope.split():
        raise AuthConfigValidationError(
            "OIDCを有効化するには scope に openid が必要です。"
        )
    return normalized_scope


def save_oidc_config(
    db: Session,
    app_settings: AppSettings,
    *,
    enabled: bool,
    issuer: str,
    client_id: str,
    client_secret: str,
    scope: str,
) -> AuthConfig:
    """singleton OIDC configをvalidation付きでupsertする。

    client secret未入力時は、同一client identityの既存ciphertextを保持する。issuer/client IDを
    変更した場合は旧secretを破棄し、enable時は必要項目と復号可能性をcommit前に検証する。

    Args:
        db: configを更新するDB session。
        app_settings: redirect URIや暗号鍵を含むruntime settings。
        enabled: 保存後にOIDCを有効化するか。
        issuer: issuer URL candidate。
        client_id: OIDC client ID candidate。
        client_secret: 新しいclient secret。空値は既存secret保持の意図。
        scope: space-separated OIDC scope。

    Returns:
        保存済みsingleton AuthConfig row。

    Raises:
        AuthConfigValidationError: enableに必要な設定不足、scope不正、secret復号不可の場合。
    """
    normalized_issuer = issuer.strip() or None
    normalized_client_id = client_id.strip() or None
    normalized_scope = scope.strip() or DEFAULT_OIDC_SCOPE
    if enabled:
        normalized_scope = validate_oidc_scope_for_enable(normalized_scope)
    new_secret = client_secret

    existing = get_auth_config(db)
    encrypted_secret = (
        str(existing.oidc_client_secret_encrypted)
        if existing is not None and existing.oidc_client_secret_encrypted
        else None
    )
    client_identity_changed = existing is not None and (
        normalized_issuer != existing.oidc_issuer
        or normalized_client_id != existing.oidc_client_id
    )

    if new_secret:
        encrypted_secret = encrypt_client_secret(
            new_secret,
            app_settings.auth_config_encryption_key,
        )
    elif (
        existing is None
        and enabled
        and normalized_issuer == app_settings.oidc_issuer
        and normalized_client_id == app_settings.oidc_client_id
        and app_settings.oidc_client_secret
    ):
        encrypted_secret = encrypt_client_secret(
            app_settings.oidc_client_secret,
            app_settings.auth_config_encryption_key,
        )
    elif client_identity_changed:
        encrypted_secret = None

    if enabled:
        missing_fields: list[str] = []
        if not normalized_issuer:
            missing_fields.append("issuer")
        if not normalized_client_id:
            missing_fields.append("client ID")
        if not app_settings.oidc_redirect_uri:
            missing_fields.append("OIDC_REDIRECT_URL")
        if encrypted_secret is None:
            missing_fields.append("client secret")
        if missing_fields:
            raise AuthConfigValidationError(
                "OIDCを有効化するには " + ", ".join(missing_fields) + " が必要です。"
            )

        # Re-enabling with a preserved ciphertext must prove that this replica has
        # the matching external key before the database row is marked enabled.
        if not new_secret and encrypted_secret is not None:
            decrypt_client_secret(
                encrypted_secret,
                app_settings.auth_config_encryption_key,
            )

    with transaction(db):
        config = existing
        if config is None:
            config = AuthConfig(id=AUTH_CONFIG_ID)
            db.add(config)
        config.oidc_enabled = enabled
        config.oidc_issuer = normalized_issuer
        config.oidc_client_id = normalized_client_id
        config.oidc_client_secret_encrypted = encrypted_secret
        config.oidc_scope = normalized_scope
        db.flush()

    return config


def unlink_oidc_config(db: Session) -> AuthConfig:
    """OIDC DB設定を明示disabled状態へ初期化する。

    Args:
        db: configを更新するDB session。

    Returns:
        OIDC値をclearし、disabledを保存したsingleton AuthConfig row。
    """
    with transaction(db):
        config = get_auth_config(db)
        if config is None:
            config = AuthConfig(id=AUTH_CONFIG_ID)
            db.add(config)
        config.oidc_enabled = False
        config.oidc_issuer = None
        config.oidc_client_id = None
        config.oidc_client_secret_encrypted = None
        config.oidc_scope = DEFAULT_OIDC_SCOPE
        db.flush()

    return config


async def check_oidc_discovery(
    issuer: str,
    timeout: float,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """未保存issuer candidateのOIDC discovery metadataを取得・検証する。

    Args:
        issuer: discovery対象issuer URL。
        timeout: HTTP timeout秒。
        transport: test等で差し替えるoptional HTTPX transport。

    Returns:
        必須endpointとissuer整合性を検証済みのdiscovery metadata。

    Raises:
        OIDCDiscoveryError: issuer未入力、通信/JSON failure、必須項目不足、issuer不一致の場合。
    """
    normalized_issuer = issuer.strip()
    if not normalized_issuer:
        raise OIDCDiscoveryError("issuerを入力してください。")

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        ) as client:
            response = await client.get(oidc_discovery_url(normalized_issuer))
            response.raise_for_status()
            metadata = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCDiscoveryError("OIDC discovery metadataを取得できません。") from exc

    if not isinstance(metadata, dict):
        raise OIDCDiscoveryError("OIDC discovery metadataの形式が不正です。")

    required = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri")
    if any(
        not isinstance(metadata.get(name), str) or not metadata[name]
        for name in required
    ):
        raise OIDCDiscoveryError("OIDC discovery metadataに必須項目がありません。")

    expected_issuer = normalized_issuer
    if metadata["issuer"] != expected_issuer:
        raise OIDCDiscoveryError(
            "OIDC discovery metadataのissuerが入力値と一致しません。"
        )

    return metadata
