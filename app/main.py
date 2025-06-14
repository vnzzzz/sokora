"""
Sokora Webアプリケーションのメインエントリーポイント
==============================================

FastAPIアプリケーションの設定と初期化を行います。
"""

from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

# ローカルモジュールのインポート
from app.routers.api.v1 import router as api_v1_router  # API v1用ルーター
from app.routers.pages import router as pages_router       # UIページ用ルーター
from app.core.config import APP_VERSION, logger
from app.db.session import initialize_database

# APIタグ定義
API_TAGS: List[Dict[str, str]] = [
    {
        "name": "Pages",
        "description": "アプリケーションUIページとカレンダー表示用エンドポイント",
    },
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


def create_application() -> FastAPI:
    """アプリケーションインスタンスを作成します。

    Returns:
        FastAPI: 設定済みのFastAPIアプリケーションインスタンス
    """
    app = FastAPI(
        title="Sokora API",
        description="勤怠管理システムSokora APIのドキュメント",
        version=APP_VERSION,
        docs_url="/docs",  # デフォルトの/docsを有効化
        redoc_url="/redoc",  # デフォルトの/redocを有効化
    )

    # /staticから静的ファイルを提供（開発時ファイル用）
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # /assetsからビルド時生成ファイルを提供（本番ファイル用）
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

    # UIページ用ルーターを組み込み
    app.include_router(pages_router)
    
    # API v1用ルーターを組み込み
    app.include_router(api_v1_router)

    return app


def create_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """カスタムOpenAPIスキーマを生成します。
    
    Args:
        app: FastAPIアプリケーションインスタンス
        
    Returns:
        Dict[str, Any]: 生成されたOpenAPIスキーマ
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Sokora API",
        version=APP_VERSION,
        description="勤怠管理システムSokora APIのドキュメント",
        routes=app.routes,
    )

    # OpenAPIバージョンを明示的に設定
    openapi_schema["openapi"] = "3.0.2"
    # タグの順序とカスタム説明を追加
    openapi_schema["tags"] = API_TAGS

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# アプリケーションインスタンスの作成
app = create_application()

# OpenAPIスキーマの設定
app.openapi = lambda: create_openapi_schema(app)  # type: ignore


# アプリケーション起動時の初期化処理
@app.on_event("startup")
async def startup_event() -> None:
    """アプリケーション起動時の初期化処理を実行します。
    
    データベースの初期化などの処理を行います。
    """
    logger.info("Initializing database")
    initialize_database()
