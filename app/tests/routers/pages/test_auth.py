import base64
import json
import re
import urllib.parse

import pytest
from httpx import ASGITransport, AsyncClient
from itsdangerous import TimestampSigner

from app.core.settings import AppSettings
from app.main import app, create_application
from app.services.auth.dependencies import (
    get_oidc_client,
    get_optional_oidc_client,
)
from app.services.auth.oidc import OIDCError, OIDCStateError


class DummyOIDCResult:
    """テスト用のOIDC認証結果。token属性はsession非保持の確認にだけ使う。"""

    def __init__(
        self,
        subject: str = "oidc-user",
        username: str = "oidc-user",
        id_token: str = "id-token",
        access_token: str = "access-token",
        refresh_token: str | None = "refresh-token",
    ) -> None:
        self.subject = subject
        self.username = username
        self.id_token = id_token
        self.access_token = access_token
        self.refresh_token = refresh_token


class FakeOIDCClient:
    """route testで外部OIDC通信を置き換えるapplication境界のfake。"""

    def __init__(
        self,
        *,
        fail: bool = False,
        invalid_state: bool = False,
        result: DummyOIDCResult | None = None,
    ) -> None:
        self.fail = fail
        self.invalid_state = invalid_state
        self.result = result or DummyOIDCResult()

    async def build_authorization_url(
        self,
        *,
        request,
        redirect_uri: str | None = None,
    ) -> str:
        del request
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": "client-id",
                "redirect_uri": redirect_uri,
                "state": "fake-state",
                "nonce": "fake-nonce",
            }
        )
        return f"https://idp.example/authorize?{query}"

    async def exchange_code(self, *, request) -> DummyOIDCResult:
        del request
        if self.invalid_state:
            raise OIDCStateError("state mismatch")
        if self.fail:
            raise OIDCError("OIDC provider unavailable")
        return self.result

    async def get_logout_url(
        self,
        *,
        request,
        post_logout_redirect_uri: str,
    ) -> str | None:
        del request, post_logout_redirect_uri
        return None

    async def validate_logout_response(self, request) -> None:
        del request


class RecordingLogoutOIDCClient(FakeOIDCClient):
    """RP-Initiated Logoutのcallback URIを記録するfake。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.last_logout_redirect: str | None = None

    async def get_logout_url(
        self,
        *,
        request,
        post_logout_redirect_uri: str,
    ) -> str | None:
        del request
        self.last_logout_redirect = post_logout_redirect_uri
        query = urllib.parse.urlencode(
            {
                "client_id": "client-id",
                "post_logout_redirect_uri": post_logout_redirect_uri,
                "state": "logout-state",
            }
        )
        return f"https://idp.example/logout?{query}"


@pytest.mark.asyncio
async def test_oidc_login_allows_protected_api(async_client, monkeypatch) -> None:
    """OIDC正常系で最小identity sessionが作られ、保護APIへアクセスできること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient()
    try:
        redirect_resp = await async_client.get(
            "/auth/redirect?next=/analysis", follow_redirects=False
        )
        assert redirect_resp.status_code == 307
        assert redirect_resp.headers["location"].startswith(
            "https://idp.example/authorize?"
        )

        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=fake-state",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303
        assert callback_resp.headers["location"] == "/analysis"

        api_resp = await async_client.get("/api/v1/locations")
        assert api_resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_oidc_failure_allows_local_admin_fallback(
    async_client, monkeypatch
) -> None:
    """OIDC障害時もlocal admin経路を利用者が選択できること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient(fail=True)
    try:
        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=fake-state",
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
async def test_guard_blocks_when_not_authenticated(async_client, monkeypatch) -> None:
    """認証必須時に未ログインだとUIはloginへ、APIは401を返すこと。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")

    page_resp = await async_client.get("/attendance/weekly", follow_redirects=False)
    assert page_resp.status_code == 307
    assert page_resp.headers["location"].startswith("/auth/login")

    api_resp = await async_client.get("/api/v1/locations")
    assert api_resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_oidc_config_returns_400(async_client, monkeypatch) -> None:
    """OIDC必須設定が無い状態ではOIDCフローを開始しないこと。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_ID", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OIDC_REDIRECT_URL", raising=False)

    resp = await async_client.get("/auth/redirect", follow_redirects=False)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oidc_callback_rejects_invalid_state(async_client, monkeypatch) -> None:
    """OIDC clientがstate不一致を検出した場合は400で拒否すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient(
        invalid_state=True
    )
    try:
        resp = await async_client.get(
            "/auth/callback?code=test-code&state=wrong-state",
            follow_redirects=False,
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_auth_settings_is_admin_only_and_read_only(
    async_client, monkeypatch
) -> None:
    """認証設定はlocal adminだけが参照でき、runtime toggleを提供しないこと。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    unauthenticated = await async_client.get("/auth/settings")
    assert unauthenticated.status_code == 401

    login_resp = await async_client.post(
        "/auth/local",
        data={
            "username": "admin",
            "password": "secret",
            "next": "/auth/settings",
        },
        follow_redirects=False,
    )
    assert login_resp.status_code == 303

    settings_page = await async_client.get("/auth/settings")
    assert settings_page.status_code == 200
    assert "環境変数/secret" in settings_page.text
    assert "/auth/settings/oidc/toggle" not in settings_page.text


@pytest.mark.asyncio
async def test_session_cookie_contains_identity_only(async_client, monkeypatch) -> None:
    """OIDC tokenを永続cookieへ保持せず最小identityだけを保持すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    result = DummyOIDCResult(
        id_token="id-token-value",
        access_token="A" * 3000,
        refresh_token="R" * 3000,
    )
    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient(result=result)
    try:
        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=fake-state",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        session_cookie = async_client.cookies.get("session")
        assert session_cookie
        assert "id-token-value" not in session_cookie
        assert "A" * 100 not in session_cookie
        assert "R" * 100 not in session_cookie

        session_secret = next(
            m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware"
        ).options["secret_key"]
        signer = TimestampSigner(session_secret)
        unsigned = signer.unsign(session_cookie.encode("utf-8"))
        payload = unsigned.rsplit(b".", 1)[0]
        session_data = json.loads(base64.b64decode(payload))

        assert session_data["auth"] == {
            "method": "oidc",
            "subject": "oidc-user",
            "username": "oidc-user",
        }
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_oidc_logout_uses_absolute_callback(async_client, monkeypatch) -> None:
    """RP-Initiated Logoutは絶対callback URIを利用しstate callbackを経由すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    recorder = RecordingLogoutOIDCClient()
    app.dependency_overrides[get_oidc_client] = lambda: recorder
    app.dependency_overrides[get_optional_oidc_client] = lambda: recorder
    try:
        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=fake-state",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        logout_resp = await async_client.post("/auth/logout", follow_redirects=False)
        assert logout_resp.status_code == 303
        assert recorder.last_logout_redirect == "http://test/auth/logout/callback"
        assert logout_resp.headers["location"].startswith("https://idp.example/logout?")

        completed = await async_client.get(
            "/auth/logout/callback?state=logout-state",
            follow_redirects=False,
        )
        assert completed.status_code == 303
        assert completed.headers["location"].startswith("/auth/login?")
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)
        app.dependency_overrides.pop(get_optional_oidc_client, None)


@pytest.mark.asyncio
async def test_next_redirect_rejects_external_url(async_client, monkeypatch) -> None:
    """認証後redirect先としてscheme-relative external URLを受け入れないこと。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.post(
        "/auth/local",
        data={
            "username": "admin",
            "password": "secret",
            "next": "//evil.example/phishing",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


@pytest.mark.asyncio
async def test_secure_session_cookie_flags() -> None:
    """HTTPS production session cookieにSecure/HttpOnly/SameSiteを付与すること。"""
    settings = AppSettings(
        auth_enabled=True,
        session_secret="test-secret",
        session_https_only=True,
        local_auth_enabled=True,
        local_admin_username="admin",
        local_admin_password="secret",
        database_url="sqlite:///:memory:",
    )
    secure_app = create_application(settings)
    transport = ASGITransport(app=secure_app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        resp = await client.post(
            "/auth/local",
            data={"username": "admin", "password": "secret", "next": "/"},
            follow_redirects=False,
        )

    assert resp.status_code == 303
    set_cookie = resp.headers["set-cookie"].lower()
    assert "secure" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


@pytest.mark.asyncio
async def test_login_page_shows_sso_and_admin_buttons(
    async_client, monkeypatch
) -> None:
    """ログインlandingはSSO優先、local adminは別導線だけを表示すること。"""
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.get("/auth/login")
    assert resp.status_code == 200
    assert "/auth/redirect" in resp.text
    assert "SSOでログイン" in resp.text
    assert "/auth/login/admin" in resp.text
    assert 'name="username"' not in resp.text


@pytest.mark.asyncio
async def test_admin_login_page_shows_form(async_client, monkeypatch) -> None:
    """local admin pageだけにusername/password formを表示すること。"""
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.get("/auth/login/admin?next=/users")
    assert resp.status_code == 200
    assert 'action="/auth/local"' in resp.text
    assert 'name="username"' in resp.text
    assert 'name="password"' in resp.text
    assert 'name="next"' in resp.text


@pytest.mark.asyncio
async def test_sidebar_hidden_on_login_page(async_client) -> None:
    """未ログイン時はlogin pageへsidebarを表示しないこと。"""
    resp = await async_client.get("/auth/login")
    assert resp.status_code == 200
    assert "<aside" not in resp.text


@pytest.mark.asyncio
async def test_sidebar_auth_settings_visible_only_for_admin(
    async_client, monkeypatch
) -> None:
    """認証設定linkはadminだけに表示すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://test/auth/callback")

    app.dependency_overrides[get_oidc_client] = lambda: FakeOIDCClient()
    try:
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

        async_client.cookies.clear()
        callback_resp = await async_client.get(
            "/auth/callback?code=test-code&state=fake-state",
            follow_redirects=False,
        )
        assert callback_resp.status_code == 303

        user_page = await async_client.get("/", follow_redirects=True)
        assert user_page.status_code == 200
        assert "認証設定" not in user_page.text
    finally:
        app.dependency_overrides.pop(get_oidc_client, None)


@pytest.mark.asyncio
async def test_header_shows_username_and_logout_button(
    async_client, monkeypatch
) -> None:
    """ログイン後headerにusernameとlogout buttonを表示すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
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
    async_client, monkeypatch
) -> None:
    """user menuをlayout外に重ねてcontent高さを変えないこと。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
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
    assert any("pt-14" in cls for cls in main_classes)


@pytest.mark.asyncio
async def test_login_page_does_not_show_logout_notice(async_client) -> None:
    """logout後のlogin pageへ不要な通知を表示しないこと。"""
    resp = await async_client.get("/auth/login?reason=logout")
    assert resp.status_code == 200
    assert "ログアウトしました。" not in resp.text


@pytest.mark.asyncio
async def test_login_page_does_not_show_session_expired_notice(async_client) -> None:
    """reauth redirect後も不要なsession expired通知を表示しないこと。"""
    resp = await async_client.get("/auth/login?reason=reauth")
    assert resp.status_code == 200
    assert "セッションが切れました。再度ログインしてください。" not in resp.text


@pytest.mark.asyncio
async def test_sidebar_shown_when_auth_not_required(async_client, monkeypatch) -> None:
    """認証不要modeでも通常pageはsidebar付きで表示すること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "false")

    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "<aside" in resp.text
    assert 'data-testid="user-menu"' not in resp.text
    assert "ゲスト" not in resp.text


@pytest.mark.asyncio
async def test_local_admin_disabled_when_flag_off(async_client, monkeypatch) -> None:
    """local auth flagがfalseならcredentialがあってもlogin不可であること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "false")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    resp = await async_client.post(
        "/auth/local",
        data={"username": "admin", "password": "secret", "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
