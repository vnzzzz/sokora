from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
import logging

# 設定ファイルのインポート
from .core.config import APP_VERSION, logger

# ルートモジュールのインポート
from .api.v1 import root, attendance, calendar

# DBモジュールのインポート
from .db.session import initialize_database

# FastAPIアプリの作成（デフォルトのドキュメントを無効化）
app = FastAPI(
    title="Sokora API",
    docs_url=None,  # デフォルトの/docsを無効化
    redoc_url=None,  # デフォルトの/redocを無効化
    version=APP_VERSION,
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
        "name": "勤怠管理",
        "description": "ユーザーの勤怠データを管理するエンドポイント",
    },
    {
        "name": "カレンダー",
        "description": "カレンダー表示と日別詳細情報のエンドポイント",
    },
    {
        "name": "ページ表示",
        "description": "アプリケーションUIページ表示用エンドポイント",
    },
]


# アプリケーション起動時の初期化処理
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化処理を実行"""
    # データベースの初期化
    logger.info("Initializing database")
    initialize_database()


# カスタムOpenAPIスキーマ定義
def custom_openapi():
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


app.openapi = custom_openapi


# カスタムSwagger UIページの提供
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    """カスタムパスでSwagger UIを提供する"""
    swagger_js = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"
    swagger_css = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css"
    openapi_url = app.openapi_url or "/openapi.json"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - APIドキュメント</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="{swagger_css}">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="{swagger_js}"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true
            }})
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    """OpenAPI JSONスキーマを提供する"""
    return app.openapi()
