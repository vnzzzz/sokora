"""
CSVダウンロードページエンドポイント
=====================

CSVデータのダウンロードページを提供します。
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any

from app.utils.csv_utils import get_available_months

# ルーター定義
router = APIRouter(prefix="/csv", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
def csv_page(request: Request) -> Any:
    """
    CSVダウンロードページを表示します

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 利用可能な月リストを取得
    months = get_available_months()
    
    return templates.TemplateResponse(
        "pages/csv/index.html", 
        {"request": request, "months": months}
    ) 