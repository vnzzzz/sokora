"""
勤務場所管理ページエンドポイント
----------------

勤務場所の設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.location import location
from app.db.session import get_db
from app.utils.ui_utils import TAILWIND_COLORS

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
    # データベースから全勤務場所を取得し、名前でソートします。
    locations_db = db.query(location.model).order_by(location.model.name).all()

    # 各勤務場所に表示用の色情報を付与します。
    locations = []
    for i, loc in enumerate(locations_db):
        color_idx = i % len(TAILWIND_COLORS)
        color_name = TAILWIND_COLORS[color_idx]
        text_color_class = f"text-{color_name}"

        locations.append({
            "id": loc.id,
            "name": loc.name,
            "color_class": text_color_class # 文字色クラスのみ
        })

    return templates.TemplateResponse(
        "pages/location/index.html", {"request": request, "locations": locations}
    ) 