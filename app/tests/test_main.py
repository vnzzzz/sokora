"""Application-level public contract tests."""

import pytest
from fastapi.testclient import TestClient

from app.core.settings import DEFAULT_SESSION_SECRET, AppSettings
from app.main import app, create_application


class TestCreateApplication:
    def test_configures_public_api_metadata(self) -> None:
        app_instance = create_application()

        assert app_instance.title == "Sokora API"
        assert app_instance.description == "勤怠管理システムSokora APIのドキュメント"
        assert app_instance.docs_url == "/docs"
        assert app_instance.redoc_url == "/redoc"

    def test_accepts_explicit_settings(self) -> None:
        settings = AppSettings(
            database_url="sqlite:///:memory:",
            log_level="DEBUG",
        )

        app_instance = create_application(settings)

        assert app_instance.state.settings_provider() is settings
        assert app_instance.version == settings.app_version

    @pytest.mark.parametrize("session_secret", ["", "   ", DEFAULT_SESSION_SECRET])
    def test_rejects_insecure_session_secret_when_auth_enabled(
        self, session_secret: str
    ) -> None:
        settings = AppSettings(
            auth_enabled=True,
            session_secret=session_secret,
        )

        with pytest.raises(ValueError, match="SOKORA_AUTH_SESSION_SECRET"):
            create_application(settings)

    @pytest.mark.parametrize("session_secret", ["", "   ", DEFAULT_SESSION_SECRET])
    def test_rejects_insecure_session_secret_for_local_admin(
        self, session_secret: str
    ) -> None:
        settings = AppSettings(
            auth_enabled=False,
            session_secret=session_secret,
            local_auth_enabled=True,
            local_admin_username="admin",
            local_admin_password="secret",
        )

        with pytest.raises(ValueError, match="SOKORA_AUTH_SESSION_SECRET"):
            create_application(settings)

    def test_missing_local_admin_credentials_keep_local_admin_disabled(self) -> None:
        settings = AppSettings(
            auth_enabled=False,
            session_secret=DEFAULT_SESSION_SECRET,
            local_auth_enabled=True,
        )

        app_instance = create_application(settings)

        assert app_instance.state.auth_enabled is False
        assert app_instance.state.local_admin_enabled is False


class TestApplicationLifespan:
    def test_initializes_and_releases_database_runtime(self) -> None:
        settings = AppSettings(database_url="sqlite:///:memory:")
        app_instance = create_application(settings)

        with TestClient(app_instance) as client:
            assert client.get("/").status_code == 200
            runtime = app_instance.state.database_runtime
            assert runtime.database_url == settings.database_url

        assert app_instance.state.database_runtime is None

    def test_in_memory_database_is_shared_with_request_sessions(self) -> None:
        settings = AppSettings(database_url="sqlite:///:memory:")
        app_instance = create_application(settings)

        with TestClient(app_instance) as client:
            response = client.get("/api/v1/locations")

        assert response.status_code == 200
        assert response.json() == {"locations": []}


class TestOpenApiContract:
    def test_openapi_endpoint_exposes_expected_metadata_and_tags(self) -> None:
        client = TestClient(app)

        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Sokora API"
        assert (
            schema["info"]["description"]
            == "勤怠管理システムSokora APIのドキュメント"
        )
        assert schema["openapi"] == "3.0.2"
        assert [tag["name"] for tag in schema["tags"]] == [
            "Attendance",
            "Locations",
            "Users",
            "Groups",
            "UserTypes",
            "Data",
        ]


class TestAppIntegration:
    def test_documentation_routes_are_available(self) -> None:
        client = TestClient(app)

        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200

    def test_legacy_ui_route_not_available(self) -> None:
        client = TestClient(app)

        response = client.get("/ui")

        assert response.status_code == 404
