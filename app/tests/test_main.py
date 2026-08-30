"""
main.py のテストケース
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.settings import AppSettings
from app.main import API_TAGS, app, create_application, create_openapi_schema


class TestCreateApplication:
    """create_application関数のテスト"""

    def test_create_application_returns_fastapi_instance(self) -> None:
        """create_application関数がFastAPIインスタンスを返すことを確認"""
        app_instance = create_application()

        assert isinstance(app_instance, FastAPI)
        assert app_instance.title == "Sokora API"
        assert app_instance.description == "勤怠管理システムSokora APIのドキュメント"
        assert app_instance.docs_url == "/docs"
        assert app_instance.redoc_url == "/redoc"

    def test_create_application_accepts_explicit_settings(self) -> None:
        settings = AppSettings(
            database_url="sqlite:///:memory:",
            log_level="DEBUG",
        )

        app_instance = create_application(settings)

        assert app_instance.state.settings_provider() is settings
        assert app_instance.version == settings.app_version

    def test_create_application_includes_routers(self) -> None:
        """create_application関数がルーターを含むことを確認"""
        app_instance = create_application()

        assert len(app_instance.routes) > 0

        client = TestClient(app_instance)

        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/static/test.css")
        assert response.status_code in [200, 404]


class TestApplicationLifespan:
    def test_lifespan_initializes_and_releases_database_runtime(self) -> None:
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


class TestCreateOpenApiSchema:
    """create_openapi_schema関数のテスト"""

    def test_create_openapi_schema_new_schema(self) -> None:
        """新しいOpenAPIスキーマの生成テスト"""
        app_instance = create_application()
        app_instance.openapi_schema = None

        schema = create_openapi_schema(app_instance)

        assert schema is not None
        assert schema["info"]["title"] == "Sokora API"
        assert schema["openapi"] == "3.0.2"
        assert "tags" in schema
        assert schema["tags"] == API_TAGS

    def test_create_openapi_schema_existing_schema(self) -> None:
        """既存のOpenAPIスキーマを返すテスト"""
        app_instance = create_application()
        existing_schema = {"test": "schema"}
        app_instance.openapi_schema = existing_schema

        schema = create_openapi_schema(app_instance)

        assert schema == existing_schema

    @patch("app.main.get_openapi")
    def test_create_openapi_schema_calls_get_openapi(
        self, mock_get_openapi: MagicMock
    ) -> None:
        """get_openapi関数が正しい引数で呼ばれることを確認"""
        app_instance = create_application()
        app_instance.openapi_schema = None

        mock_schema = {
            "info": {"title": "Test", "version": "1.0.0"},
            "openapi": "3.0.0",
        }
        mock_get_openapi.return_value = mock_schema

        create_openapi_schema(app_instance)
        mock_get_openapi.assert_called_once()
        call_args = mock_get_openapi.call_args
        assert call_args[1]["title"] == "Sokora API"
        assert call_args[1]["description"] == "勤怠管理システムSokora APIのドキュメント"
        assert call_args[1]["routes"] == app_instance.routes


class TestAppInstance:
    """アプリケーションインスタンスのテスト"""

    def test_app_instance_is_fastapi(self) -> None:
        """appインスタンスがFastAPIであることを確認"""
        assert isinstance(app, FastAPI)

    def test_app_has_custom_openapi(self) -> None:
        """appインスタンスがカスタムopenapi関数を持つことを確認"""
        assert hasattr(app, "openapi")
        assert callable(app.openapi)

    def test_app_openapi_returns_schema(self) -> None:
        """app.openapi()がスキーマを返すことを確認"""
        schema = app.openapi()

        assert schema is not None
        assert "info" in schema
        assert "openapi" in schema


class TestApiTags:
    """API_TAGSの定義テスト"""

    def test_api_tags_structure(self) -> None:
        """API_TAGSが正しい構造を持つことを確認"""
        assert isinstance(API_TAGS, list)
        assert len(API_TAGS) > 0

        for tag in API_TAGS:
            assert "name" in tag
            assert "description" in tag
            assert isinstance(tag["name"], str)
            assert isinstance(tag["description"], str)

    def test_api_tags_contains_expected_tags(self) -> None:
        """公開APIのOpenAPIタグが期待どおりであることを確認"""
        tag_names = [tag["name"] for tag in API_TAGS]

        expected_tags = [
            "Attendance",
            "Locations",
            "Users",
            "Groups",
            "UserTypes",
            "Data",
        ]

        assert tag_names == expected_tags


class TestAppIntegration:
    """アプリケーション統合テスト"""

    def test_app_basic_routes(self) -> None:
        """基本的なルートが動作することを確認"""
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200

    def test_legacy_ui_route_not_available(self) -> None:
        """旧 /ui プレフィックスが無効化されていることを確認"""
        client = TestClient(app)

        response = client.get("/ui")

        assert response.status_code == 404
