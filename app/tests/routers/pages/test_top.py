"""Top page public behavior tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_top_page_renders_public_content() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Sokora" in response.text
    assert "勤怠管理" in response.text
