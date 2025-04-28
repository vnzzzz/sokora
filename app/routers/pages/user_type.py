"""
社員種別管理ページエンドポイント
----------------

社員種別の設定管理に関連するルートハンドラー
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.user_type import user_type
from app.db.session import get_db

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/user_types", response_class=HTMLResponse)
def user_type_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員種別管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    user_types = user_type.get_multi(db)
    return templates.TemplateResponse(
        "pages/user_type/index.html", {"request": request, "user_types": user_types}
    ) 