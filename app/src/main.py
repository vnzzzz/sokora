from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
import os

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ルートモジュールの導入
from .routes import root, attendance, calendar, csv

app = FastAPI(title="Sokora勤務管理アプリ")

# 静的ファイルを /static で配信
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# 各モジュールのルーターをアプリケーションに含める
app.include_router(root.router)
app.include_router(attendance.router)
app.include_router(calendar.router)
app.include_router(csv.router)
