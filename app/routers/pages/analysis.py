"""
勤怠集計ページエンドポイント
================

勤怠集計に関連するルートハンドラー
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.services import analysis_read_service

router = APIRouter(prefix="/analysis", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_analysis_page(
    request: Request,
    month: Optional[str] = None,
    year: Optional[int] = None,
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """勤怠集計ページを表示します。"""
    try:
        view_model = analysis_read_service.get_analysis_page_view_model(
            db,
            month=month,
            year=year,
            mode=mode,
        )
    except Exception as exc:
        logger.error(
            "勤怠集計ページ表示中にエラーが発生しました: %s",
            exc,
            exc_info=True,
        )
        view_model = analysis_read_service.get_error_page_view_model(month=month)

    return templates.TemplateResponse(
        "pages/analysis.html",
        {"request": request, **view_model},
    )
