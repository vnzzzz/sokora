from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("next_path", "expected_next"),
    [
        ("/users", "/users"),
        ("//evil.example/phishing", "/"),
    ],
)
async def test_failed_local_admin_login_returns_to_admin_form(
    async_client,
    monkeypatch,
    next_path: str,
    expected_next: str,
) -> None:
    """認証失敗時も安全なnextを保ったまま管理者フォームで再試行できること。"""
    monkeypatch.setenv("SOKORA_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SOKORA_LOCAL_ADMIN_PASSWORD", "secret")

    response = await async_client.post(
        "/auth/local",
        data={
            "username": "admin",
            "password": "wrong-password",
            "next": next_path,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    redirect = urlsplit(response.headers["location"])
    assert redirect.path == "/auth/login/admin"
    assert parse_qs(redirect.query) == {
        "next": [expected_next],
        "reason": ["local_failed"],
    }

    retry_page = await async_client.get(response.headers["location"])
    assert retry_page.status_code == 200
    assert "管理者認証に失敗しました。" in retry_page.text
    assert 'name="username"' in retry_page.text
    assert 'name="password"' in retry_page.text
    assert f'name="next" value="{expected_next}"' in retry_page.text
