import base64
import json
import re
import urllib.parse

import pytest
from itsdangerous import TimestampSigner

from app.main import app

# 依存性オーバーライド用のインポート（未実装のため型チェックのみで使用）
from app.services.auth.dependencies import (
    get_oidc_client,
    get_optional_oidc_client,
)  # type: ignore[import-not-found]


class DummyOIDCResult:
    """テスト用の簡易 OIDC 結果オブジェクト"""

    def __init__(
        self,
        subject: str = "kc-user",
        username: str = "kc-user",
        id_token: str = "id-token",
        access_token: str = "access-token",
        refresh_token: str | None = None,
    ) -> None:
        self.subject = subject
        self.username = username
        self.id_token = id_token
        self.access_token = access_token
        self.refresh_token = refresh_token


class FakeOIDCClient:
    """Keycloak への外部通信を行わないテスト用クライアント"""

    def __init__(self, fail: bool = False, result: DummyOIDCResult | None = None) -> None:
        self.fail = fail
        self.result = result or DummyOIDCResult()
        self.authorization_endpoint = "http://keycloak.example.com/auth"

    def build_authorization_url(
        self,
        state: str,
        nonce: str,
        redirect_uri: str | None = None,
        scope: str = "openid profile email",
    ) -> str:
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": "client-id",
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "nonce": nonce,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    def exchange_code(
        self,
        code: str,
        state: str,
        nonce: str,
        redirect_uri: str | None = None,
    ) -> DummyOIDCResult:
        if self.fail:
            raise RuntimeError("Keycloak unreachable")
        return self.result


class RecordingLogoutOIDCClient(FakeOIDCClient):
    """ログアウト時の post_logout_redirect_uri を記録するテスト用クライアント"""

    def __init__(self, logout_endpoint: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.logout_endpoint = logout_endpoint
        self.last_logout_redirect: str | None = None

    def get_logout_url(self, id_token_hint: str, post_logout_redirect_uri: str) -> str | None:  # type: ignore[override]
        self.last_logout_redirect = post_logout_redirect_uri
        query = urllib.parse.urlencode(
            {"id_token_hint": id_token_hint, "post_logout_redirect_uri": post_logout_redirect_uri}
        )
        return f"{self.logout_endpoint}?{query}"


@pytest.mark.asyncio
async def test_oidc_login_allows_protected_api(async_client, monkeypatch, tmp_path) -> None:
    """Keycloak 正常系でセッションが作られ、ガード済み API へアクセスできること"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient()
    try:
        redirect_resp = await async_client.get(
            "/auth/redirect?next=/analysis",
            follow_redirects=False,
        )
        assert redirect_resp.status_code == 307
        redirect_target = redirect_resp.headers["location"]
        params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_target).query)
        state = params["state"][0]

        callback_resp = await async_client.get(
            f"/auth/callback?code=test-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303
        assert callback_resp.headers["location"] == "/analysis"

        api_resp = await async_client.get("/api/v1/locations")
        assert api_resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_keycloak_failure_allows_local_admin_fallback(async_client, monkeypatch, tmp_path) -> None:
    """Keycloak 障害時にローカル管理者ログインへ切り替えられること"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient(fail=True)
    try:
        redirect_resp = await async_client.get("/auth/redirect", follow_redirects=False)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_resp.headers["location"]).query)
        state = params["state"][0]

        callback_resp = await async_client.get(
            f"/auth/callback?code=test-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303
        assert callback_resp.headers["location"].startswith("/auth/login")

        login_page = await async_client.get(callback_resp.headers["location"])
        assert "SSOでログイン" in login_page.text

        local_resp = await async_client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/users"},
            follow_redirects=False,
        )
        assert local_resp.status_code == 303
        assert local_resp.headers["location"] == "/users"

        api_resp = await async_client.get("/api/v1/locations")
        assert api_resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_guard_blocks_when_not_authenticated(async_client, monkeypatch, tmp_path) -> None:
    """認証必須時に未ログインだと UI はログイン画面へ、API は 401 を返す"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))

    page_resp = await async_client.get("/attendance/weekly", follow_redirects=False)
    assert page_resp.status_code == 307
    assert page_resp.headers["location"].startswith("/auth/login")

    api_resp = await async_client.get("/api/v1/locations")
    assert api_resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_oidc_config_returns_400(async_client, monkeypatch, tmp_path) -> None:
    """OIDC 必須設定が無い状態で OIDC フローを開始すると 400 になる"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_ID", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OIDC_REDIRECT_URL", raising=False)

    resp = await async_client.get("/auth/redirect", follow_redirects=False)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oidc_callback_rejects_invalid_state(async_client, monkeypatch, tmp_path) -> None:
    """state 不一致のコールバックは 400 で拒否する"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient()
    try:
        await async_client.get("/auth/redirect", follow_redirects=False)
        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=wrong-state",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_local_admin_can_toggle_oidc_off(async_client, monkeypatch, tmp_path) -> None:
    """管理者が OIDC を無効化すると OIDC フロー開始が拒否される"""
    state_path = tmp_path / "auth_state.json"
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(state_path))
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    # 管理者でログイン
    local_resp = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/auth/settings"},
        follow_redirects=False,
    )
    assert local_resp.status_code == 303

    # OIDC を無効化
    toggle_resp = await async_client.post(
        "/auth/settings/oidc/toggle",
        data={"enabled": "false"},
        follow_redirects=False,
    )
    assert toggle_resp.status_code == 303

    # OIDC フロー開始が 400 になることを確認
    resp = await async_client.get("/auth/redirect", follow_redirects=False)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_session_cookie_excludes_access_and_refresh_tokens(async_client, monkeypatch, tmp_path) -> None:
    """セッションに access_token/refresh_token を保存しない（クッキー肥大化防止）"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    large_tokens = DummyOIDCResult(
        id_token="id-token-value",
        access_token="A" * 3000,
        refresh_token="R" * 3000,
    )
    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient(result=large_tokens)
    try:
        redirect_resp = await async_client.get("/auth/redirect", follow_redirects=False)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_resp.headers["location"]).query)
        state = params["state"][0]

        callback_resp = await async_client.get(
            f"/auth/callback?code=test-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        session_cookie = async_client.cookies.get("session")
        assert session_cookie

        session_secret = next(
            m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware"
        ).options["secret_key"]

        signer = TimestampSigner(session_secret)
        unsigned = signer.unsign(session_cookie.encode("utf-8"))
        payload = unsigned.rsplit(b".", 1)[0]  # drop timestamp
        session_data = json.loads(base64.b64decode(payload))

        auth = session_data["auth"]
        assert auth["id_token"] == "id-token-value"
        assert "access_token" not in auth
        assert "refresh_token" not in auth
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_oidc_logout_uses_absolute_redirect(async_client, monkeypatch, tmp_path) -> None:
    """ログアウト時の post_logout_redirect_uri は絶対URLになる"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    recorder = RecordingLogoutOIDCClient(
        logout_endpoint="http://keycloak.example.com/realms/test/protocol/openid-connect/logout",
        result=DummyOIDCResult(id_token="id-token-value"),
    )
    app.dependency_overrides[get_oidc_client] = lambda: recorder
    app.dependency_overrides[get_optional_oidc_client] = lambda: recorder
    try:
        redirect_resp = await async_client.get("/auth/redirect", follow_redirects=False)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_resp.headers["location"]).query)
        state = params["state"][0]

        callback_resp = await async_client.get(
            f"/auth/callback?code=test-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        logout_resp = await async_client.post("/auth/logout", follow_redirects=False)
        assert logout_resp.status_code == 303
        assert recorder.last_logout_redirect == "http://test/auth/login?reason=logout"
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)
        app.dependency_overrides.pop(get_optional_oidc_client, None)


@pytest.mark.asyncio
async def test_login_page_shows_sso_and_admin_buttons(async_client, monkeypatch, tmp_path) -> None:
    """ログインランディングは SSO 優先、管理者ログインは導線だけを見せる"""
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.get("/auth/login")
    assert resp.status_code == 200
    text = resp.text
    assert "/auth/redirect" in text
    assert "SSOでログイン" in text
    assert "/auth/login/admin" in text
    assert 'name="username"' not in text


@pytest.mark.asyncio
async def test_admin_login_page_shows_form(async_client, monkeypatch, tmp_path) -> None:
    """管理者ログインページでのみユーザー名/パスワードのフォームを表示する"""
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.get("/auth/login/admin?next=/users")
    assert resp.status_code == 200
    text = resp.text
    assert 'action="/auth/local"' in text
    assert 'name="username"' in text
    assert 'name="password"' in text
    assert 'name="next"' in text


@pytest.mark.asyncio
async def test_sidebar_hidden_on_login_page(async_client, monkeypatch, tmp_path) -> None:
    """未ログイン時はサイドバーを表示しない"""
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))

    resp = await async_client.get("/auth/login")
    assert resp.status_code == 200
    assert "<aside" not in resp.text


@pytest.mark.asyncio
async def test_sidebar_auth_settings_visible_only_for_admin(async_client, monkeypatch, tmp_path) -> None:
    """認証設定リンクは管理者のみ表示し、ラベルはシンプルな表記にする"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("OIDC_ISSUER", "http://keycloak.example.com/realms/test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient()
    try:
        # 管理者ログイン時は認証設定リンクを表示する
        admin_login = await async_client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/"},
            follow_redirects=False,
        )
        assert admin_login.status_code == 303

        admin_page = await async_client.get("/", follow_redirects=True)
        assert admin_page.status_code == 200
        assert "認証設定（管理者）" not in admin_page.text
        assert "認証設定" in admin_page.text
        assert 'href="/auth/settings"' in admin_page.text

        # 一般ユーザー（OIDC）では非表示
        async_client.cookies.clear()
        redirect_resp = await async_client.get("/auth/redirect", follow_redirects=False)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_resp.headers["location"]).query)
        state = params["state"][0]

        callback_resp = await async_client.get(
            f"/auth/callback?code=test-code&state={state}",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        user_page = await async_client.get("/", follow_redirects=True)
        assert user_page.status_code == 200
        assert "認証設定（管理者）" not in user_page.text
        assert "認証設定" not in user_page.text
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_header_shows_username_and_logout_button(async_client, monkeypatch, tmp_path) -> None:
    """ログイン後はヘッダーにユーザー名とログアウトボタンを表示し、サイドバーのログアウトは無い"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    login_resp = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303

    page = await async_client.get("/", follow_redirects=True)
    assert page.status_code == 200
    assert "admin" in page.text
    assert 'data-testid="user-menu"' in page.text
    assert 'data-testid="logout-button"' in page.text
    assert 'data-testid="logout-icon"' in page.text
    assert page.text.count('action="/auth/logout"') == 1
    assert 'aria-label="ログアウト"' in page.text
    assert ">ログアウト<" not in page.text


@pytest.mark.asyncio
async def test_user_menu_is_overlay_and_does_not_shift_content(
    async_client, monkeypatch, tmp_path
) -> None:
    """ユーザーメニューをレイアウト外に重ねてコンテンツ高さを変えない"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    login_resp = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303

    page = await async_client.get("/", follow_redirects=True)
    assert page.status_code == 200

    match = re.search(
        r'<header[^>]*class="([^"]+)"[^>]*data-testid="user-menu-wrapper"',
        page.text,
    )
    assert match, "user menu wrapper should be present"
    classes = match.group(1)
    assert "fixed" in classes
    assert "right-0" in classes
    assert "justify-end" in classes

    main_classes = re.findall(r'class="([^"]+)"', page.text)
    assert any("pt-14" in cls for cls in main_classes), "main should reserve top padding"


@pytest.mark.asyncio
async def test_login_page_does_not_show_logout_notice(async_client, monkeypatch, tmp_path) -> None:
    """ログアウト後にログイン画面へ戻っても通知メッセージは表示しない"""
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))

    resp = await async_client.get("/auth/login?reason=logout")
    assert resp.status_code == 200
    assert "ログアウトしました。" not in resp.text


@pytest.mark.asyncio
async def test_login_page_does_not_show_session_expired_notice(
    async_client, monkeypatch, tmp_path
) -> None:
    """セッション切れ理由でリダイレクトされても通知メッセージは表示しない"""
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))

    resp = await async_client.get("/auth/login?reason=reauth")
    assert resp.status_code == 200
    assert "セッションが切れました。再度ログインしてください。" not in resp.text


@pytest.mark.asyncio
async def test_sidebar_shown_when_auth_not_required(async_client, monkeypatch, tmp_path) -> None:
    """認証不要モードでも通常ページはサイドバー付きで表示する"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "false")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))

    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "<aside" in resp.text
    assert 'data-testid="user-menu"' not in resp.text
    assert "ゲスト" not in resp.text


@pytest.mark.asyncio
async def test_local_admin_disabled_when_flag_off(async_client, monkeypatch, tmp_path) -> None:
    """ローカル管理者の有効フラグが false の場合は認証不可にする"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_AUTH_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("SOKORA_AUTH_STATE_PATH", str(tmp_path / "auth_state.json"))
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "false")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
