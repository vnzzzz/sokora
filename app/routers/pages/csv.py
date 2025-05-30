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
    # CSVダウンロード対象として選択可能な月のリストを取得します。
    months = get_available_months()
    
    return templates.TemplateResponse(
        "pages/csv.html", 
        {"request": request, "months": months}
    ) 