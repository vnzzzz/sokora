"""SokoraのFastAPI application lifecycleと共通HTTP boundaryを定義する。

router個別のbusiness ruleは各adapter/serviceへ委譲し、このmoduleではapplication startup、
shared middleware、health probe、OpenAPIといったprocess全体のcontractだけを所有する。
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import configure_logging, logger
from app.core.settings import AppSettings
from app.db.session import (
    DatabaseRuntime,
    get_app_database_runtime,
    initialize_database,
)
from app.middleware.auth import AuthRequiredMiddleware
from app.routers.api.v1 import router as api_v1_router
from app.routers.pages import router as pages_router
from app.services.auth.settings import AuthSettings
from app.services.errors import ApplicationError

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
        "description": "CSVデータを出力するエンドポイント",
    },
]


async def health_check(request: Request) -> JSONResponse:
    """processがrequestを安全に処理できるかをplatform probeへ返す。

    通常はHTTP 200を返す。SQLite restore/recovery失敗後にDatabaseRuntimeが
    fail-closedへfenceされた場合はHTTP 503を返し、platformがそのprocessを
    healthyなreplicaとして扱わないようにする。

    unavailable reasonにはfilesystem path等の内部情報が含まれ得るため、responseへは
    公開せずstatusだけを返す。認証を要求しないこともdeployment runtime contractの一部。
    """
    runtime = getattr(request.app.state, "database_runtime", None)
    if isinstance(runtime, DatabaseRuntime) and runtime.unavailable_reason is not None:
        # Fenced runtimeへ再接続させない判断はDatabaseRuntimeが所有する。
        # health endpointはその状態を外部orchestratorへ503として投影するだけに留める。
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse({"status": "ok"})


async def application_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """adapterで未処理のApplicationErrorをpublic JSON errorへ変換する。

    HTML/HTMX page adapterは画面固有fragmentを返すため、write handler内で
    ApplicationErrorを処理する。ここではJSON API側から漏れたapplication errorだけを
    共通形式へ変換し、未知のexceptionは誤って正常化せず再送出する。
    """
    if not isinstance(exc, ApplicationError):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """startup時点のruntime設定を検証し、DB schema準備後にrequest受付を開始する。

    lifespan開始時にsettings providerから取得したinstanceへvalidationを適用し、Alembic
    migrationを完了してfresh file-backed SQLiteだけをseedする。providerが後から返す別instance
    までこのvalidationで保証するわけではないため、running processのconfig hot-reloadは
    application contractに含めない。migration/seed failureは握り潰さずlifespan startupを
    失敗させ、applicationは未更新schemaのままtrafficを受けない。

    shutdownではprocess-owned DatabaseRuntimeをdisposeし、次のapplication instanceが
    stale engine/session factoryを再利用しないようapp stateから切り離す。
    """
    settings: AppSettings = app.state.settings_provider()
    settings.validate_runtime()
    app.state.settings = settings
    configure_logging(settings.log_level)

    runtime = get_app_database_runtime(app)
    logger.info("Initializing database")
    try:
        initialize_database(runtime)
        yield
    finally:
        runtime.dispose()
        app.state.database_runtime = None


def create_application(settings: AppSettings | None = None) -> FastAPI:
    """shared middleware・router・lifespanを組み込んだFastAPI applicationを作成する。

    ``settings``を明示した場合は、そのobjectをapplication lifetime中の設定providerとして
    再利用する。主にtestや埋め込みruntimeでprocess environmentから切り離すための入口。
    省略時は``AppSettings.from_env``をproviderとして保持するため、provider呼び出しごとに
    process environmentから新しいsettings instanceを構築し得る。

    ただしSessionMiddlewareのsecret/max-age/cookie属性など、application作成時に固定される
    componentもある。process environmentを変更してrunning processをhot-reconfigureする
    contractは提供せず、runtime config/secret変更はprocess restartで全componentへ一貫して
    適用する。

    DB engine自体はここで作成せずlifespanでapplication instanceへbindする。これにより
    import時にDB接続を開始せず、startup validation/migrationより先にrequest resourceを
    公開しない。
    """
    settings_provider: Callable[[], AppSettings]
    if settings is None:
        settings_provider = AppSettings.from_env
        initial_settings = settings_provider()
    else:
        initial_settings = settings

        def explicit_settings_provider() -> AppSettings:
            return initial_settings

        settings_provider = explicit_settings_provider

    initial_settings.validate_runtime()

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
    app.add_exception_handler(ApplicationError, application_error_handler)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

    app.add_api_route(
        "/healthz",
        health_check,
        methods=["GET"],
        include_in_schema=False,
    )
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
        same_site="lax",
        https_only=auth_settings.session_https_only,
    )

    return app


def create_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """JSON API routerだけを対象とするSokoraのOpenAPI schemaを生成・cacheする。

    page/HTMX routerと`/healthz`はapplication routeとして存在するがOpenAPIから除外する。
    schemaはapplication instanceへcacheし、同一process内で毎回再構築しない。
    """
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
