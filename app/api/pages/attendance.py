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
    # 月の処理
    if month is None:
        month = get_current_month_formatted()
        logger.debug(f"月パラメータなし。デフォルト設定: {month}")
    else:
        # 月の形式を検証
        try:
            year, month_num = parse_month(month)
            # フォーマットを統一
            month = f"{year}-{month_num:02d}"
            logger.debug(f"月パラメータ検証成功: {month}")
        except ValueError as e:
            logger.warning(f"無効な月パラメータ: {month}, エラー: {str(e)}")
            # 現在の月にリダイレクト
            current_month = get_current_month_formatted()
            return RedirectResponse(url=f"/attendance?month={current_month}")
    
    # カレンダーデータを取得
    logger.debug(f"カレンダーデータ取得: {month}")
    calendar_data = build_calendar_data(db, month)
    
    if not calendar_data or "weeks" not in calendar_data:
        logger.error(f"カレンダーデータの取得に失敗: {month}")
        # 現在の月にフォールバック
        month = get_current_month_formatted()
        calendar_data = build_calendar_data(db, month)
    
    # 全ユーザー取得
    all_users = user.get_all_users(db)
    
    # 検索クエリがある場合、フィルタリング
    if search_query and search_query.strip():
        search_term = search_query.lower().strip()
        filtered_users = [
            (user_name, user_id, user_type_id) for user_name, user_id, user_type_id in all_users
            if search_term in user_name.lower() or search_term in user_id.lower()
        ]
        base_users = filtered_users
    else:
        base_users = all_users
    
    # ユーザーオブジェクトを追加
    users = []
    for user_name, user_id, user_type_id in base_users:
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if user_obj:
            users.append((user_name, user_id, user_type_id, user_obj))
    
    # グループ情報を取得
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}
    
    # ユーザータイプ情報を取得
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}
    
    # ユーザーをグループごとに整理
    grouped_users: Dict[str, List] = {}
    
    for user_name, user_id, user_type_id, user_obj in users:
        # グループ情報を取得
        group_obj = None
        if user_obj.group_id in groups_map:
            group_obj = groups_map[user_obj.group_id]
        
        group_name = str(group_obj.name) if group_obj else "未分類"
        
        # グループごとのリストに追加
        if group_name not in grouped_users:
            grouped_users[group_name] = []
        
        grouped_users[group_name].append((user_name, user_id, user_type_id, user_obj))
    
    # 各グループ内でユーザーを社員種別でソート
    for g_name in list(grouped_users.keys()):
        grouped_users[g_name].sort(key=lambda u: u[2])  # user_type_id でソート
    
    # 勤務場所タイプの取得
    location_types = location.get_all_locations(db)
    
    # 勤務場所スタイルの生成
    location_styles = generate_location_styles(location_types)
    
    # 各ユーザーの勤怠データを取得
    user_attendances = {}
    user_attendance_locations = {}
    
    for user_name, user_id, user_type_id, user_obj in users:
        # ユーザーの勤怠データを取得
        user_entries = attendance.get_user_data(db, user_id=user_id)
        
        # ユーザーの勤怠日付とロケーションをマッピング
        user_dates = {}
        locations_map = {}
        
        for entry in user_entries:
            date = entry["date"]
            user_dates[date] = True
            locations_map[date] = entry["location_name"]
        
        user_attendances[user_id] = user_dates
        user_attendance_locations[user_id] = locations_map
    
    # カレンダーの日数をカウント（colspan用）
    calendar_day_count = 0
    for week in calendar_data["weeks"]:
        for day in week:
            if day and day.get("day", 0) != 0:
                calendar_day_count += 1
    
    # 共通コンテキスト
    context = {
        "request": request, 
        "users": users, 
        "groups": groups, 
        "user_types": user_types,
        "grouped_users": grouped_users,
        "group_names": sorted(list(grouped_users.keys())),
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
    
    # HTMXリクエストの場合はテーブル部分のみを返す
    if request.headers.get("HX-Request") == "true":
        logger.debug("HTMXリクエストを検出。部分テンプレートを返します。")
        return templates.TemplateResponse(
            "pages/attendance/attendance_content.html", context,
            headers={"HX-Reswap": "innerHTML"}
        )
    
    # 通常のリクエストの場合は完全なページを返す
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