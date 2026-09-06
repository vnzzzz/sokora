from fastapi.testclient import TestClient

from app.core.settings import AppSettings
from app.main import create_application


def test_healthz_is_available_without_authentication() -> None:
    """Health probes must not depend on an authenticated user session."""
    settings = AppSettings(
        database_url="sqlite:///:memory:",
        auth_enabled=True,
        session_secret="test-session-secret",
    )

    with TestClient(create_application(settings)) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_reports_fenced_database_runtime_unavailable() -> None:
    settings = AppSettings(database_url="sqlite:///:memory:")
    app = create_application(settings)

    with TestClient(app) as client:
        runtime = app.state.database_runtime
        runtime.mark_unavailable("forced recovery failure")

        response = client.get("/healthz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}

def test_fenced_database_runtime_rejects_csv_download_without_leaking_reason() -> None:
    settings = AppSettings(database_url="sqlite:///:memory:")
    app = create_application(settings)

    with TestClient(app) as client:
        runtime = app.state.database_runtime
        runtime.mark_unavailable("forced recovery failure at /internal/database/path")

        response = client.get("/api/v1/csv/download?month=2032-05")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    assert "forced recovery failure" not in response.text
    assert "/internal/database/path" not in response.text

