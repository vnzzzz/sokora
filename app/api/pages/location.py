"""
勤務場所管理ページエンドポイント
----------------

勤務場所の設定管理に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.location import location

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/locations", response_class=HTMLResponse)
def location_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤務場所管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    locations = location.get_all_locations(db)
    return templates.TemplateResponse(
        "pages/location/index.html", {"request": request, "locations": locations}
    ) 