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
import time

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

# カレンダーデータのキャッシュ（パフォーマンス最適化）
_calendar_cache: Dict[str, Dict[str, Any]] = {}
_calendar_cache_ttl = 60  # キャッシュの有効期間（秒）
_calendar_cache_timestamp: Dict[str, float] = {}


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

    # キャッシュチェック（パフォーマンス最適化）
    current_time = time.time()
    if month in _calendar_cache and current_time - _calendar_cache_timestamp.get(month, 0) < _calendar_cache_ttl:
        calendar_data = _calendar_cache[month]
    else:
        # カレンダーデータを生成してキャッシュする
        calendar_data = build_calendar_data(db, month)
        _calendar_cache[month] = calendar_data
        _calendar_cache_timestamp[month] = current_time
    
    # 今日の日付をフォーマットして取得
    today_date = get_today_formatted()

    context = {
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
        "today_date": today_date  # テンプレートに今日の日付を渡す
    }
    return templates.TemplateResponse("components/calendar/linear_calendar.html", context)


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

    # attendance.get_day_data から返されるデータを attendance_data として使用します。
    attendance_data = detail

    # グループ情報をIDをキーとする辞書として取得します。
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}

    # 全勤務場所名を取得します。
    location_types = location.get_all_locations(db)

    # 勤務場所名に対応するUIバッジ情報を生成します。
    locations = generate_location_badges(location_types)
    locations_badge_map = {loc["name"]: loc["badge"] for loc in locations}

    # UI表示用に、勤務場所ごとにユーザーをグルーピングします。
    organized_data: Dict[str, Dict[str, Any]] = {}
    for location_name, users_list in attendance_data.items():
        # 各勤務場所内で、ユーザーを所属グループごとに整理します。
        grouped_users: Dict[str, List] = {}
        for user_data in users_list:
            user_obj = user.get_by_user_id(db, user_id=user_data["user_id"])
            if not user_obj:
                continue

            group_obj = groups_map.get(user_obj.group_id)
            group_name = str(group_obj.name) if group_obj else "未分類"

            user_data["group_id"] = str(user_obj.group_id)
            user_data["group_name"] = group_name

            if group_name not in grouped_users:
                grouped_users[group_name] = []

            grouped_users[group_name].append(user_data)

        # 各グループ内のユーザーリストを社員種別IDでソートします。
        for g_name in list(grouped_users.keys()):
            grouped_users[g_name].sort(key=lambda u: u.get("user_type_id", 999))

        # 整理したデータを勤務場所名をキーとして格納します。
        organized_data[location_name] = {
            "groups": grouped_users,
            "group_names": sorted(list(grouped_users.keys())) # グループ名をソートして格納
        }

    # さらに、グループを主キーとしてユーザーを整理するデータ構造も作成します。
    organized_by_group: Dict[str, Dict[str, Any]] = {}
    # グループIDとグループ名のマッピング (ソート用)
    group_id_to_name = {g.group_id: g.name for g in groups}
    sorted_groups = sorted(groups, key=lambda g: int(g.group_id) if g.group_id is not None else 9999)
    sorted_group_names = [str(g.name) for g in sorted_groups]

    # ユーザー種別IDと名前のマッピング (ソート用)
    user_type_id_to_name = {ut.user_type_id: ut.name for ut in user_types}
    user_type_id_mapping = {}

    # 全勤怠データを再度ループし、グループ主キーのデータ構造を構築します。
    for location_name, users_list in attendance_data.items():
        location_badge = locations_badge_map.get(location_name, "neutral")

        for user_data in users_list:
            # ユーザーデータに必要な情報を追加します。
            user_data["location_name"] = location_name
            user_data["location_badge"] = location_badge

            user_obj = user.get_by_user_id(db, user_id=user_data["user_id"])
            if not user_obj:
                continue

            group_obj = groups_map.get(user_obj.group_id)
            group_name = str(group_obj.name) if group_obj else "未分類"

            # 社員種別情報を取得し、ソート用のIDマッピングも更新します。
            user_type_name = "未分類"
            user_type_id = 9999
            if user_obj.user_type_id in user_types_map:
                user_type_obj = user_types_map[user_obj.user_type_id]
                user_type_name = str(user_type_obj.name)
                user_type_id = int(user_type_obj.user_type_id)
                user_type_id_mapping[user_type_name] = user_type_id

            # グループキーの辞書が存在しない場合は初期化します。
            if group_name not in organized_by_group:
                organized_by_group[group_name] = {
                    "user_types": set(), # このグループに含まれる社員種別名のセット
                    "user_types_data": {}, # 社員種別名をキーとするユーザーリストの辞書
                    "group_id": int(user_obj.group_id) if user_obj.group_id is not None else 9999
                }

            organized_by_group[group_name]["user_types"].add(user_type_name)

            # 社員種別キーのリストが存在しない場合は初期化します。
            if user_type_name not in organized_by_group[group_name]["user_types_data"]:
                organized_by_group[group_name]["user_types_data"][user_type_name] = []

            organized_by_group[group_name]["user_types_data"][user_type_name].append(user_data)

    # 各グループ内の社員種別リストを、社員種別IDに基づいてソートします。
    for group_name in organized_by_group:
        sorted_user_types = sorted(
            list(organized_by_group[group_name]["user_types"]),
            key=lambda ut: user_type_id_mapping.get(ut, 9999)
        )
        organized_by_group[group_name]["user_types"] = sorted_user_types

    # 最終的なグループ主キーの辞書を、グループIDに基づいてソートします。
    sorted_organized_by_group = dict(sorted(
        organized_by_group.items(),
        key=lambda item: item[1].get("group_id", 9999)
    ))

    # この日に勤怠データが存在するかどうかのフラグを設定します。
    has_data = bool(attendance_data) and any(len(users) > 0 for users in attendance_data.values())

    # テンプレートに渡すコンテキストを作成します。
    context = {
        "request": request,
        "day": day,
        "data": detail, # 元の get_day_data の結果も渡す
        "locations": locations, # UI用バッジ情報
        "has_data": has_data,
        "attendance_data": attendance_data, # 加工前の勤怠データ
        "organized_data": organized_data, # 勤務場所主キーで整理されたデータ
        "organized_by_group": sorted_organized_by_group, # グループ主キーで整理・ソートされたデータ
        "target_date": day
    }

    return templates.TemplateResponse("pages/main/day_detail.html", context) 