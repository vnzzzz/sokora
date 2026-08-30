"""Sokora FastAPI application factory."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import configure_logging, logger
from app.core.settings import AppSettings
from app.db.session import get_app_database_runtime, initialize_database
from app.middleware.auth import AuthRequiredMiddleware
from app.routers.api.v1 import router as api_v1_router
from app.routers.pages import router as pages_router
from app.services.auth.settings import AuthSettings
from app.utils.holiday_cache import refresh_holiday_cache

API_TAGS: List[Dict[str, str]] = [
    {
        "name": "Attendance",
        "description": "ユーザーの勤怠データを管理するエンドポイント",
    },
    {
        "name": "Locations",
        "description": "勤怠種別を管理するエンドポイント",
    },
    {
        "name": "Users",
        "description": "ユーザーを管理するエンドポイント",
    },
    {
        "name": "Groups",
        "description": "グループを管理するエンドポイント",
    },
    {
        "name": "UserTypes",
        "description": "社員種別を管理するエンドポイント",
    },
    {
        "name": "Data",
        "description": "CSVを管理するエンドポイント",
    },
]


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and release application-scoped runtime resources."""
    settings: AppSettings = app.state.settings_provider()
    app.state.settings = settings
    configure_logging(settings.log_level)

    runtime = get_app_database_runtime(app)
    logger.info("Initializing database")
    initialize_database(runtime)

    db = runtime.session_factory()
    try:
        refresh_holiday_cache(db)
    finally:
        db.close()

    try:
        yield
    finally:
        runtime.dispose()
        app.state.database_runtime = None


def create_application(settings: AppSettings | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    Passing ``settings`` gives tests and alternate runtimes an explicit,
    process-environment-independent configuration. Without an explicit object,
    the provider reads the current environment when runtime startup begins.
    """
    settings_provider: Callable[[], AppSettings]
    if settings is None:
        settings_provider = AppSettings.from_env
        initial_settings = settings_provider()
    else:
        settings_provider = lambda: settings
        initial_settings = settings

    app = FastAPI(
        title="Sokora API",
        description="勤怠管理システムSokora APIのドキュメント",
        version=initial_settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=application_lifespan,
    )
    app.state.settings_provider = settings_provider
    app.state.settings = initial_settings

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

    app.include_router(pages_router, include_in_schema=False)
    app.include_router(api_v1_router)

    auth_settings = AuthSettings.from_app_settings(initial_settings)
    app.state.auth_enabled = auth_settings.auth_enabled
    app.add_middleware(
        AuthRequiredMiddleware,
        settings_provider=lambda: AuthSettings.from_app_settings(settings_provider()),
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=auth_settings.session_secret,
        max_age=auth_settings.session_ttl_seconds,
    )

    return app


def create_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Create the custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    settings: AppSettings = app.state.settings_provider()
    openapi_schema = get_openapi(
        title="Sokora API",
        version=settings.app_version,
        description="勤怠管理システムSokora APIのドキュメント",
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.0.2"
    openapi_schema["tags"] = API_TAGS

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = create_application()
app.openapi = lambda: create_openapi_schema(app)  # type: ignore
