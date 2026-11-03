"""
CSVダウンロードページエンドポイント
=====================

CSVデータのダウンロードページを提供するルートハンドラー
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.utils.csv_utils import get_available_months

router = APIRouter(prefix="/csv", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def csv_page(request: Request) -> Any:
    """CSV download pageをrenderする。

    Args:
        request: FastAPI request。

    Returns:
        選択可能な月一覧を含むCSV download page HTML。
    """
    months = get_available_months()

    return templates.TemplateResponse(
        "pages/csv.html", {"request": request, "months": months}
    )
