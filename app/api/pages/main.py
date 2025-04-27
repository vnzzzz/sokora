"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any
from sqlalchemy.orm import Session

from app.db.session import get_db

# ページ表示用ルーター
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def root_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """トップページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # シンプルなコンテキストのみを返す
    context = {
        "request": request,
    }
    return templates.TemplateResponse("pages/index.html", context) 