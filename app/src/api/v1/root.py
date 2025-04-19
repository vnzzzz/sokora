"""
ルートページ表示
----------------

メインページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.location import location as location_crud
from ...crud.attendance import attendance
from ...utils.date_utils import get_today_formatted
from ...utils.ui_utils import generate_location_badges, has_data_for_day

router = APIRouter(tags=["ページ表示"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/", response_class=HTMLResponse)
def root_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Display the top page

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered HTML page
    """
    today_str = get_today_formatted()

    # 今日の日付のデータを取得
    default_data = attendance.get_day_data(db, day=today_str)

    # 全ての勤務場所を取得
    locations = location_crud.get_all_locations(db)

    # バッジを生成
    location_badges = generate_location_badges(locations)

    # データの有無を確認
    default_has_data = has_data_for_day(default_data)

    context = {
        "request": request,
        "default_day": today_str,
        "default_data": default_data,
        "default_locations": location_badges,
        "default_has_data": default_has_data,
    }
    return templates.TemplateResponse("base.html", context)
