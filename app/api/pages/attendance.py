"""
勤怠管理ページエンドポイント
----------------

勤怠登録・管理ページに関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.crud.user import user
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.group import group
from app.crud.user_type import user_type
from app.utils.date_utils import get_current_month_formatted
from app.utils.ui_utils import generate_location_styles
from app.utils.calendar_utils import build_calendar_data, parse_month

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

# ロガー定義
logger = logging.getLogger(__name__)


@router.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request, 
    search_query: Optional[str] = None,
    month: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Any:
    """勤怠登録ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        search_query: 検索クエリ（社員名またはID）
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 月パラメータの処理と検証 (指定がない場合は現在の月を使用)
    if month is None:
        month = get_current_month_formatted()
        logger.debug(f"月パラメータなし。デフォルト設定: {month}")
    else:
        # YYYY-MM 形式に正規化し、無効な場合は現在の月にリダイレクト
        try:
            year, month_num = parse_month(month)
            month = f"{year}-{month_num:02d}"
            logger.debug(f"月パラメータ検証成功: {month}")
        except ValueError as e:
            logger.warning(f"無効な月パラメータ: {month}, エラー: {str(e)}")
            current_month = get_current_month_formatted()
            return RedirectResponse(url=f"/attendance?month={current_month}")

    # 指定された月のカレンダーデータを構築します。
    logger.debug(f"カレンダーデータ取得: {month}")
    calendar_data = build_calendar_data(db, month)

    # カレンダーデータの取得に失敗した場合、現在の月にフォールバックします。
    if not calendar_data or "weeks" not in calendar_data:
        logger.error(f"カレンダーデータの取得に失敗: {month}")
        month = get_current_month_formatted()
        calendar_data = build_calendar_data(db, month)

    # 全ユーザー情報を取得します。
    all_users = user.get_all_users(db)

    # 検索クエリが指定されている場合、ユーザーをフィルタリングします。
    if search_query and search_query.strip():
        search_term = search_query.lower().strip()
        filtered_users = [
            (user_name, user_id, user_type_id) for user_name, user_id, user_type_id in all_users
            if search_term in user_name.lower() or search_term in user_id.lower()
        ]
        base_users = filtered_users
    else:
        base_users = all_users

    # フィルタリング後のユーザーリストに、完全なUserオブジェクトを追加します。
    users = []
    for user_name, user_id, user_type_id in base_users:
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if user_obj:
            users.append((user_name, user_id, user_type_id, user_obj))

    # グループ情報をIDをキーとする辞書として取得します。
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}

    # 表示用にユーザーをグループ名でグルーピングします。
    grouped_users: Dict[str, List] = {}
    for user_name, user_id, user_type_id, user_obj in users:
        group_obj = groups_map.get(user_obj.group_id)
        group_name = str(group_obj.name) if group_obj else "未分類"

        if group_name not in grouped_users:
            grouped_users[group_name] = []

        grouped_users[group_name].append((user_name, user_id, user_type_id, user_obj))

    # 各グループ内のユーザーリストを社員種別IDでソートします。
    for g_name in list(grouped_users.keys()):
        grouped_users[g_name].sort(key=lambda u: u[2])

    # 利用可能な全勤務場所名を取得します。
    location_types = location.get_all_locations(db)

    # 勤務場所名に対応するCSSクラスを生成します。
    location_styles = generate_location_styles(location_types)

    # 各ユーザーの勤怠データを日付をキーとして取得・整形します。
    user_attendances = {}
    user_attendance_locations = {}
    for user_name, user_id, user_type_id, user_obj in users:
        user_entries = attendance.get_user_data(db, user_id=user_id)

        user_dates = {} # 特定の日に勤怠データが存在するか (True/False)
        locations_map = {} # 特定の日の勤務場所名

        for entry in user_entries:
            date_str = entry["date"]
            user_dates[date_str] = True
            locations_map[date_str] = entry["location_name"]

        user_attendances[user_id] = user_dates
        user_attendance_locations[user_id] = locations_map

    # カレンダーの表示日数を計算 (テーブルのcolspan用)
    calendar_day_count = 0
    for week in calendar_data["weeks"]:
        for day in week:
            if day and day.get("day", 0) != 0:
                calendar_day_count += 1

    # テンプレートに渡すコンテキストを作成します。
    context = {
        "request": request,
        "users": users,
        "groups": groups,
        "user_types": user_types,
        "grouped_users": grouped_users,
        "group_names": sorted(list(grouped_users.keys())), # グループ名をソートして渡す
        "calendar_data": calendar_data["weeks"],
        "month_name": calendar_data["month_name"],
        "prev_month": calendar_data["prev_month"],
        "next_month": calendar_data["next_month"],
        "location_types": location_types,
        "location_styles": location_styles,
        "user_attendances": user_attendances,
        "user_attendance_locations": user_attendance_locations,
        "calendar_day_count": calendar_day_count,
    }

    # 現在選択中の月 (YYYY-MM) をコンテキストに追加
    context["current_month"] = month

    # HTMXリクエストの場合、勤怠テーブル部分のみをレンダリングして返します。
    if request.headers.get("HX-Request") == "true":
        logger.debug("HTMXリクエストを検出。部分テンプレートを返します。")
        return templates.TemplateResponse(
            "pages/attendance/attendance_content.html", context,
            headers={"HX-Reswap": "innerHTML"} # HTMXに入れ替え方法を指定
        )

    # 通常のGETリクエストの場合、完全なHTMLページをレンダリングして返します。
    logger.debug("通常リクエスト。完全なページを返します。")
    return templates.TemplateResponse(
        "pages/attendance/index.html", context
    )


@router.get("/attendance/edit/{user_id}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """ユーザーの勤怠編集ページを表示します（レガシーサポート用）

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集対象のユーザーID
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 新しい勤怠登録画面にリダイレクト
    return RedirectResponse(url="/attendance") 