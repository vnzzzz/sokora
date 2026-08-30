"""
グループ管理ページエンドポイント
----------------

グループの設定管理に関連するルートハンドラー
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.group import group
from app.db.session import get_db

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/groups", response_class=HTMLResponse)
def group_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """グループ管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    groups = group.get_multi(db)
    return templates.TemplateResponse(
        "pages/group/index.html", {"request": request, "groups": groups}
    ) 