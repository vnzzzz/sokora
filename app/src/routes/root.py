"""
ルート（トップページ）の表示
----------------

メインページの表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .. import csv_store
from ..utils.date_utils import get_today_formatted
from ..utils.common import generate_location_badges, has_data_for_day

router = APIRouter(tags=["ページ表示"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/", response_class=HTMLResponse)
def root_page(request: Request) -> HTMLResponse:
    """トップページを表示する

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    today_str = get_today_formatted()
    day_data = csv_store.get_day_data(today_str)

    # 勤務場所の種類を取得
    location_types = csv_store.get_location_types()

    # 勤務場所のバッジ情報を生成
    locations = generate_location_badges(location_types)

    # データがあるかどうかをチェック
    has_data = has_data_for_day(day_data)

    context = {
        "request": request,
        "default_day": today_str,
        "default_data": day_data,
        "default_locations": locations,
        "default_has_data": has_data,
    }
    return templates.TemplateResponse("base.html", context)
