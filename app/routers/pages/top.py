"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import calendar_read_service

# ページ表示用ルーター
router = APIRouter(prefix="", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

logger = logging.getLogger(__name__)


@router.get(
    "/", response_class=HTMLResponse, tags=["Pages"], summary="トップページ表示"
)
def read_root(request: Request, db: Session = Depends(get_db)) -> Response:
    """トップページと当月calendarを単一responseでレンダリングして返す。"""
    logger.info("Top page accessed")
    calendar_view_model = calendar_read_service.get_month_view_model(db)
    context = {
        "request": request,
        "title_text": "Sokora - 勤怠管理",
        **calendar_view_model,
    }
    return templates.TemplateResponse("pages/top.html", context)
