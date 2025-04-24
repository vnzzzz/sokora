"""
勤怠管理ページエンドポイント
----------------

勤怠登録・管理ページに関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.user import user
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.group import group
from app.crud.user_type import user_type
from app.utils.date_utils import get_current_month_formatted
from app.utils.ui_utils import generate_location_styles
from app.utils.calendar_utils import build_calendar_data

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request, 
    search_query: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Any:
    """勤怠登録ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        search_query: 検索クエリ（社員名またはID）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
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
    
    # HTMXリクエストの場合はテーブル部分のみを返す
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            "components/details/attendance_table.html", {
                "request": request, 
                "users": users,
                "grouped_users": grouped_users,
                "group_names": sorted(list(grouped_users.keys()))
            }
        )
    
    # 通常のリクエストの場合は完全なページを返す
    return templates.TemplateResponse(
        "pages/attendance/index.html", {
            "request": request, 
            "users": users, 
            "groups": groups, 
            "user_types": user_types,
            "grouped_users": grouped_users,
            "group_names": sorted(list(grouped_users.keys()))
        }
    )


@router.get("/attendance/edit/{user_id}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """ユーザーの勤怠編集ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集対象のユーザーID
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    if month is None:
        month = get_current_month_formatted()

    # Get calendar data for the specified month
    calendar_data = build_calendar_data(db, month)

    # Get user name
    user_name = user.get_user_name_by_id(db, user_id=user_id)

    # Get user data
    user_entries = attendance.get_user_data(db, user_id=user_id)
    # ユーザーリストを取得（全ユーザー）
    all_users = user.get_all_users(db)
    all_user_ids = [user_id for user_name, user_id, user_type_id in all_users]

    if not user_entries and user_id not in all_user_ids:
        raise HTTPException(status_code=404, detail=f"User ID '{user_id}' not found")

    # Create a map of dates and work locations for the user
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location_name"]

    # Get types of work locations
    location_types = location.get_all_locations(db)

    # Generate style information for work locations
    location_styles = generate_location_styles(location_types)

    # 前月と翌月の情報はcalendar_dataから取得可能
    prev_month = calendar_data["prev_month"]
    next_month = calendar_data["next_month"]

    context = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month,
        "next_month": next_month,
        "month_name": calendar_data["month_name"],
        "editable": True,  # 編集可能モード
    }

    return templates.TemplateResponse("pages/attendance/edit.html", context) 