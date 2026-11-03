"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.utils.calendar_utils import get_today_formatted

router = APIRouter(prefix="", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

logger = logging.getLogger(__name__)


@router.get(
    "/", response_class=HTMLResponse, tags=["Pages"], summary="トップページ表示"
)
def read_root(request: Request) -> Response:
    """トップページをrenderする。

    Args:
        request: FastAPI request。

    Returns:
        現在日を含むトップページHTML response。
    """
    logger.info("Top page accessed")
    context = {
        "request": request,
        "title_text": "Sokora - 勤怠管理",
        "today_date": get_today_formatted(),
    }
    return templates.TemplateResponse("pages/top.html", context)
