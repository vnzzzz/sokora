"""
勤務場所管理ページエンドポイント
----------------

勤務場所の設定管理に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, List, Dict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.location import location
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
    # 勤務場所の取得
    locations_db = db.query(location.model).order_by(location.model.name).all()
    
    # 勤務場所に色情報を追加
    locations = []
    for i, loc in enumerate(locations_db):
        color_idx = i % len(TAILWIND_COLORS)
        color_name = TAILWIND_COLORS[color_idx]
        bg_color_class = f"bg-{color_name}/10"
        text_color_class = f"text-{color_name}"
        color_class = f"{bg_color_class} {text_color_class} px-2 py-1 rounded"
        
        locations.append({
            "location_id": loc.location_id,
            "name": loc.name,
            "color_class": color_class
        })
    
    return templates.TemplateResponse(
        "pages/location/index.html", {"request": request, "locations": locations}
    ) 