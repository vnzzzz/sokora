from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
import logging
from typing import Dict, Any

# 設定ファイルのインポート
from .core.config import APP_VERSION, logger

# ルートモジュールのインポート
from .api.v1 import pages
from .api.v1 import api_router

# DBモジュールのインポート
from .db.session import initialize_database

# FastAPIアプリの作成（デフォルトのドキュメントを有効化）
app = FastAPI(
    title="Sokora API",
    description="勤怠管理システムSokora APIのドキュメント",
    version=APP_VERSION,
    docs_url="/docs",  # デフォルトの/docsを有効化
    redoc_url="/redoc",  # デフォルトの/redocを有効化
)

# /staticから静的ファイルを提供
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 各モジュールからルーターを組み込む
app.include_router(pages.router)  # ページ表示用統合ルーター
app.include_router(api_router)  # API用ルーター

# APIタグ定義
API_TAGS = [
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
        "description": "勤務場所を管理するエンドポイント",
    },
    {
        "name": "Users",
        "description": "ユーザーを管理するエンドポイント",
    },
]


# アプリケーション起動時の初期化処理
@app.on_event("startup")
async def startup_event() -> None:
    """アプリケーション起動時の初期化処理を実行"""
    # データベースの初期化
    logger.info("Initializing database")
    initialize_database()


# カスタムOpenAPIスキーマ定義
def custom_openapi() -> Dict[str, Any]:
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


# FastAPIのメソッドを動的に変更
app.openapi = custom_openapi  # type: ignore
