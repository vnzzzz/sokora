"""
ページ表示エンドポイント
----------------

HTMLページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any, Dict, List
import html
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user
from ...crud.attendance import attendance
from ...crud.location import location
from ...crud.group import group
from ...crud.user_type import user_type
from ...utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ...utils.ui_utils import (
    generate_location_badges,
    has_data_for_day,
    generate_location_styles,
)
from ...utils.calendar_utils import build_calendar_data
from ...core.config import logger

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
    today_str = get_today_formatted()

    # 今日の日付のデータを取得
    default_data = attendance.get_day_data(db, day=today_str)

    # 全ての勤務場所を取得
    locations = location.get_all_locations(db)

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


@router.get("/user", response_class=HTMLResponse)
def user_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    users_data = user.get_all_users(db)
    users = []
    
    # ユーザーオブジェクトも含める
    for user_name, user_id, user_type_id in users_data:
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
    
    return templates.TemplateResponse(
        "user.html", {
            "request": request, 
            "users": users, 
            "groups": groups, 
            "user_types": user_types,
            "grouped_users": grouped_users,
            "group_names": sorted(list(grouped_users.keys()))
        }
    )


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
            "partials/attendance_table.html", {
                "request": request, 
                "users": users,
                "grouped_users": grouped_users,
                "group_names": sorted(list(grouped_users.keys()))
            }
        )
    
    # 通常のリクエストの場合は完全なページを返す
    return templates.TemplateResponse(
        "attendance.html", {
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

    return templates.TemplateResponse("attendance_edit.html", context)


@router.get("/locations", response_class=HTMLResponse)
def location_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤務場所管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    locations = location.get_all_locations(db)
    return templates.TemplateResponse(
        "location.html", {"request": request, "locations": locations}
    )


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
        "group.html", {"request": request, "groups": groups}
    )


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
        "user_type.html", {"request": request, "user_types": user_types}
    )


# カレンダー関連ページエンドポイント
# 元々pages_calendar.pyにあったエンドポイントを統合

@router.get("/calendar", response_class=HTMLResponse)
def get_calendar(
    request: Request, month: Optional[str] = None, db: Session = Depends(get_db)
) -> Any:
    """指定された月のカレンダーを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたカレンダーHTML
    """
    if month is None:
        month = get_current_month_formatted()

    # 今日の日付をフォーマットして取得
    today_date = get_today_formatted()

    calendar_data = build_calendar_data(db, month)
    context = {
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
        "today_date": today_date  # テンプレートに今日の日付を渡す
    }
    return templates.TemplateResponse("partials/calendar.html", context)


@router.get("/day/{day}", response_class=HTMLResponse)
def get_day_detail(
    request: Request, day: str, db: Session = Depends(get_db)
) -> Any:
    """指定された日の詳細を表示します

    Args:
        request: FastAPIリクエストオブジェクト
        day: 日付（YYYY-MM-DD形式）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされた日別詳細HTML
    """
    detail = attendance.get_day_data(db, day=day)
    
    # attendance_dataとしてdetailを設定
    attendance_data = detail

    # グループ情報を取得
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}

    # ユーザータイプ情報を取得
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}

    # 勤務場所ごとにユーザーをグループ化・整理
    organized_data: Dict[str, Dict[str, Any]] = {}
    
    for location_name, users_list in attendance_data.items():
        # ユーザーをグループごとに整理
        grouped_users: Dict[str, List[Dict[str, Any]]] = {}
        
        for user_data in users_list:
            # ユーザーの完全なオブジェクトを取得
            user_obj = user.get_by_user_id(db, user_id=user_data["user_id"])
            if not user_obj:
                continue
                
            # グループ情報を取得
            group_obj = None
            if user_obj.group_id in groups_map:
                group_obj = groups_map[user_obj.group_id]
            
            group_name = str(group_obj.name) if group_obj else "未分類"
            
            # ユーザーデータにグループ情報を追加
            user_data["group_id"] = str(user_obj.group_id)
            user_data["group_name"] = group_name
            
            # グループごとのリストに追加
            if group_name not in grouped_users:
                grouped_users[group_name] = []
            
            grouped_users[group_name].append(user_data)
        
        # 各グループ内でユーザーを社員種別でソート
        for g_name in list(grouped_users.keys()):
            grouped_users[g_name].sort(key=lambda u: u.get("user_type_id", 999))
        
        # データを整理
        organized_data[location_name] = {
            "groups": grouped_users,
            "group_names": sorted(list(grouped_users.keys()))
        }

    # Generate badge information for work locations
    location_types = location.get_all_locations(db)
    locations = generate_location_badges(location_types)

    # Check if data exists
    has_data = has_data_for_day(detail)

    context = {
        "request": request,
        "day": day,
        "data": detail,
        "locations": locations,
        "has_data": has_data,
        "attendance_data": attendance_data,
        "organized_data": organized_data,
        "target_date": day  # day_detail.htmlで使用されるtarget_dateも追加
    }
    
    return templates.TemplateResponse("partials/day_detail.html", context)


@router.get("/user/{user_id}", response_class=HTMLResponse)
def get_user_detail(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """特定のユーザーに関する詳細情報を表示

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: ユーザーID
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたユーザー詳細HTML
    """
    try:
        if month is None:
            month = get_current_month_formatted()

        # カレンダーデータを取得
        calendar_data = build_calendar_data(db, month)
        
        # ユーザー名を取得
        user_name = user.get_user_name_by_id(db, user_id=user_id)
        if not user_name:
            return HTMLResponse(f"ユーザー '{html.escape(user_id)}' が見つかりません", status_code=404)
        
        # ユーザーオブジェクトから社員種別情報を取得
        user_obj = user.get_by_user_id(db, user_id=user_id)
        user_type_name = user_obj.user_type.name if user_obj and user_obj.user_type else ""
        user_type_id = user_obj.user_type_id if user_obj else 0
        
        # ユーザーの勤怠データ取得
        user_entries = attendance.get_user_data(db, user_id=user_id)
        
        # 日付と勤務場所のマップを作成
        user_dates = []
        user_locations = {}
        for entry in user_entries:
            date = entry["date"]
            user_dates.append(date)
            user_locations[date] = entry["location_name"]
        
        # 勤務場所の種類を取得
        location_types = location.get_all_locations(db)
        
        # 勤務場所のスタイル情報を生成
        location_styles = generate_location_styles(location_types)
        
        # 表示用の日付
        last_viewed_date = get_last_viewed_date(request)
        
        context = {
            "request": request,
            "user_id": user_id,
            "user_name": user_name,
            "calendar_data": calendar_data["weeks"],
            "user_dates": user_dates,
            "user_locations": user_locations,
            "location_styles": location_styles,
            "prev_month": calendar_data["prev_month"],
            "next_month": calendar_data["next_month"],
            "last_viewed_date": last_viewed_date,
            "month_name": calendar_data["month_name"],  # 月名を追加
            "location_types": location_types,  # 勤務場所の種類も追加
            "editable": False,  # 閲覧専用モード
            "user_type_name": user_type_name,
            "user_type_id": user_type_id,
        }
        
        return templates.TemplateResponse("partials/user_detail.html", context)
    except Exception as e:
        logger.error(f"Error getting user detail: {str(e)}")
        return HTMLResponse(f"エラーが発生しました: {html.escape(str(e))}", status_code=500)


@router.get("/day/{day}/user/{user_id}", response_class=HTMLResponse)
def get_day_user_detail(
    request: Request,
    day: str,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """指定された日付の特定ユーザーの詳細を表示します

    Args:
        request: FastAPIリクエストオブジェクト
        day: 日付（YYYY-MM-DD形式）
        user_id: ユーザーID
        month: 月（YYYY-MM形式、指定がない場合は日付から抽出）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたユーザー詳細HTML
    """
    try:
        # ユーザー名を取得
        user_name = user.get_user_name_by_id(db, user_id=user_id)
        if not user_name:
            return HTMLResponse(f"ユーザー '{html.escape(user_id)}' が見つかりません", status_code=404)
        
        # ユーザーオブジェクトから社員種別情報を取得
        user_obj = user.get_by_user_id(db, user_id=user_id)
        user_type_name = user_obj.user_type.name if user_obj and user_obj.user_type else ""
        user_type_id = user_obj.user_type_id if user_obj else 0
        
        # 月を決定（引数があれば使用、なければ日付から抽出）
        if month is None:
            month = "-".join(day.split("-")[:2])
        
        # カレンダーデータを取得
        calendar_data = build_calendar_data(db, month)
        
        # ユーザーの勤怠データ取得
        user_entries = attendance.get_user_data(db, user_id=user_id)
        
        # 日付と勤務場所のマップを作成
        user_dates = []
        user_locations = {}
        for entry in user_entries:
            date = entry["date"]
            user_dates.append(date)
            user_locations[date] = entry["location_name"]
        
        # 勤務場所の種類を取得
        location_types = location.get_all_locations(db)
        
        # 勤務場所のスタイル情報を生成
        location_styles = generate_location_styles(location_types)
        
        context = {
            "request": request,
            "user_id": user_id,
            "user_name": user_name,
            "calendar_data": calendar_data["weeks"],
            "user_dates": user_dates,
            "user_locations": user_locations,
            "location_styles": location_styles,
            "prev_month": calendar_data["prev_month"],
            "next_month": calendar_data["next_month"],
            "last_viewed_date": day,
            "month_name": calendar_data["month_name"],
            "location_types": location_types,
            "editable": False,  # 閲覧専用モード
            "user_type_name": user_type_name,
            "user_type_id": user_type_id,
            "target_date": day,  # 元の日付に戻るためのパラメーター
        }
        
        return templates.TemplateResponse("partials/user_detail.html", context)
    except Exception as e:
        logger.error(f"Error getting day user detail: {str(e)}")
        return HTMLResponse(f"エラーが発生しました: {html.escape(str(e))}", status_code=500) 