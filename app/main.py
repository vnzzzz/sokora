from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
import logging
from typing import Dict, Any

# 設定ファイルのインポート
from .core.config import APP_VERSION, logger

# ルートモジュールのインポート
from .api.v1 import root, attendance, calendar

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
app.include_router(root.router)
app.include_router(attendance.page_router)  # ページ表示用ルーター
app.include_router(attendance.router)  # API用ルーター
app.include_router(calendar.router)


# APIタグ定義
API_TAGS = [
    {
        "name": "Attendance",
        "description": "ユーザーの勤怠データを管理するエンドポイント",
    },
    {
        "name": "Calendar",
        "description": "カレンダー表示と日別詳細情報のエンドポイント",
    },
    {
        "name": "Pages",
        "description": "アプリケーションUIページ表示用エンドポイント",
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
