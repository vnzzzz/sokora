"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from typing import Any
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db

# ページ表示用ルーター
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse, tags=["Pages"], summary="トップページ表示")
def read_root(request: Request) -> Response:
    """トップページをレンダリングして返す。"""
    logger.info("Top page accessed")
    context = {"request": request, "title_text": "Sokora - 勤怠管理"}
    return templates.TemplateResponse("pages/main/index.html", context) 