"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

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