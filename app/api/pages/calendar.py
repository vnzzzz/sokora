"""
カレンダーページエンドポイント
----------------

カレンダー表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Optional, Dict, List
import html
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.user import user
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.group import group
from app.crud.user_type import user_type
from app.utils.date_utils import get_today_formatted, get_current_month_formatted, get_last_viewed_date
from app.utils.ui_utils import generate_location_badges, has_data_for_day, generate_location_styles
from app.utils.calendar_utils import build_calendar_data
from app.core.config import logger

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


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
    return templates.TemplateResponse("components/calendar/calendar.html", context)


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
        grouped_users: Dict[str, List] = {}
        
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
    
    return templates.TemplateResponse("components/details/day_detail.html", context)


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
        
        return templates.TemplateResponse("components/details/user_detail.html", context)
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
        
        return templates.TemplateResponse("components/details/user_detail.html", context)
    except Exception as e:
        logger.error(f"Error getting day user detail: {str(e)}")
        return HTMLResponse(f"エラーが発生しました: {html.escape(str(e))}", status_code=500) 