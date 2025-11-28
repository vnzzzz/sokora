"""
カレンダーページエンドポイント
----------------

カレンダー表示に関連するルートハンドラー
"""

import html
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta
import calendar

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.crud.group import group
from app.crud.location import location as location_crud
from app.crud.calendar import calendar_crud
from app.crud.user import user
from app.crud.user_type import user_type
from app.db.session import get_db
from app.utils.calendar_utils import (
    build_calendar_data,
    get_current_month_formatted,
    get_today_formatted,
    parse_month,
    format_date_jp,
    parse_date
)
from app.utils.ui_utils import (
    generate_location_badges,
    get_location_color_classes,
)
from app.models.location import Location

# ルーター定義
router = APIRouter(prefix="/ui/calendar", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

# カレンダーデータのキャッシュ（パフォーマンス最適化）
_calendar_cache: Dict[str, Dict[str, Any]] = {}
_calendar_cache_ttl = 60  # キャッシュの有効期間（秒）
_calendar_cache_timestamp: Dict[str, float] = {}


@router.get("", response_class=HTMLResponse)
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
    # キャッシュされたデータ構造にはDBから取得したデータも含まれるようにする必要がある
    cached_data = _calendar_cache.get(month)
    if cached_data and current_time - _calendar_cache_timestamp.get(month, 0) < _calendar_cache_ttl:
        calendar_data = cached_data
    else:
        # DBからデータを取得
        try:
            year, month_num = parse_month(month)
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            attendances = calendar_crud.get_month_attendances(db, first_day=first_day, last_day=last_day)
            attendance_counts = calendar_crud.get_month_attendance_counts(db, first_day=first_day, last_day=last_day)
            
            # Location オブジェクトを取得 (IDを含む)
            location_objects_unsorted: List[Location] = location_crud.get_multi(db)
            location_objects = sorted(location_objects_unsorted, key=lambda loc: int(loc.id))
            location_names = [str(loc.name) for loc in location_objects]

            # 色情報を事前に生成 (Location ID -> Color Classes)
            location_color_map: Dict[int, Dict[str, str]] = {
                int(loc.id): get_location_color_classes(int(loc.id)) for loc in location_objects
            }

            # カレンダーデータを生成 (location_names を渡す)
            calendar_data = build_calendar_data(
                month=month, 
                attendances=attendances, 
                attendance_counts=attendance_counts, 
                location_types=location_names # build_calendar_data は名前のリストを期待
            )
            
            # build_calendar_dataが生成したlocationsリストに色クラスを追加
            # calendar_data['locations'] の構造は [{ 'name': str, 'color': str, 'key': str, 'badge': str }, ...]
            updated_locations = []
            for loc_data in calendar_data.get("locations", []):
                # 対応する Location オブジェクトを見つける (名前でマッチング)
                matched_loc_obj = next((loc for loc in location_objects if str(loc.name) == loc_data["name"]), None)
                if matched_loc_obj:
                    color_info = location_color_map.get(int(matched_loc_obj.id), {})
                    loc_data["text_class"] = color_info.get("text_class", "")
                    loc_data["bg_class"] = color_info.get("bg_class", "")
                    # カテゴリとorder情報を追加
                    loc_data["category"] = matched_loc_obj.category
                    loc_data["order"] = matched_loc_obj.order
                else:
                    # マッチしない場合 (エラーケース) はデフォルトを設定
                    loc_data["text_class"] = "text-gray"
                    loc_data["bg_class"] = "bg-gray/15"
                    loc_data["category"] = None
                    loc_data["order"] = None
                updated_locations.append(loc_data)
            calendar_data["locations"] = updated_locations

            # 取得した元データもキャッシュに含めるか、または build_calendar_data の結果だけをキャッシュするかは要検討
            # ここでは加工後の calendar_data をキャッシュする
            _calendar_cache[month] = calendar_data
            _calendar_cache_timestamp[month] = current_time
        except ValueError as e:
            logger.error(f"月解析エラー ({month}): {e}")
            calendar_data = None # エラー発生
        except Exception as e:
            logger.error(f"カレンダーデータ取得中にエラー ({month}): {e}", exc_info=True)
            calendar_data = None # エラー発生

    # カレンダーデータの取得に失敗した場合、現在の月にフォールバックします。
    if not calendar_data or "weeks" not in calendar_data:
        logger.error(f"カレンダーデータの取得または生成に失敗: {month}")
        # エラー時は空のカレンダー情報を設定
        calendar_data = {
            "weeks": [],
            "locations": [],
            "month_name": "エラー",
            "prev_month": month, # フォールバック用に元の月を保持
            "next_month": month
        }
        month = calendar_data["prev_month"] # エラーが発生しても month は定義されているように
    elif not all(k in calendar_data for k in ("prev_month", "next_month")):
        # prev_month や next_month が欠けている場合もエラーとして扱う
        logger.error(f"カレンダーデータに必要なキーが不足: {month}")
        calendar_data["prev_month"] = calendar_data.get("prev_month", month)
        calendar_data["next_month"] = calendar_data.get("next_month", month)
        calendar_data["month_name"] = calendar_data.get("month_name", "エラー")
    
    # 今日の日付をフォーマットして取得
    today_date = get_today_formatted()

    context = {
        "current_month": month, # YYYY-MM 形式
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
        "today_date": today_date  # テンプレートに今日の日付を渡す
    }
    # HTMXリクエストの場合、innerHTMLで入れ替えるようにヘッダーを追加
    headers = {"HX-Reswap": "innerHTML"} if request.headers.get("HX-Request") == "true" else {}
    logger.debug(f"Returning template with headers: {headers}")
    return templates.TemplateResponse(
        "components/top/summary_calendar.html", 
        context,
        headers=headers
    )


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
    groups_map = {g.id: g for g in groups}
    
    # グループのorder情報を保存する辞書
    group_orders = {g.id: (g.order if g.order is not None else float('inf')) for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.id: ut for ut in user_types}

    # 全勤怠種別オブジェクトを取得します。
    location_objects_unsorted: List[Location] = location_crud.get_multi(db)
    location_objects = sorted(location_objects_unsorted, key=lambda loc: int(loc.id))

    # 勤怠種別IDに対応するUIカラークラス情報を生成します。
    location_color_map: Dict[int, Dict[str, str]] = {
        int(loc.id): get_location_color_classes(int(loc.id)) for loc in location_objects
    }
    # テンプレートで使用する勤怠種別情報リスト (名前と色クラスを含む)
    locations_for_template = []
    for loc in location_objects:
        color_info = location_color_map.get(int(loc.id), {})
        locations_for_template.append({
            "id": int(loc.id),
            "name": str(loc.name),
            "text_class": color_info.get("text_class", ""),
            "bg_class": color_info.get("bg_class", "")
        })

    # UI表示用に、勤怠種別ごとにユーザーをグルーピングします。
    organized_data: Dict[str, Dict[str, Any]] = {}
    for location_name, users_list in attendance_data.items():
        # 各勤怠種別内で、ユーザーを所属グループごとに整理します。
        grouped_users: Dict[str, List] = {}
        for user_data in users_list:
            user_obj = user.get(db, id=user_data["user_id"])
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

        # 整理したデータを勤怠種別名をキーとして格納します。
        organized_data[location_name] = {
            "groups": grouped_users,
            "group_names": sorted(list(grouped_users.keys())) # グループ名をソートして格納
        }

    # さらに、グループを主キーとしてユーザーを整理するデータ構造も作成します。
    organized_by_group: Dict[str, Dict[str, Any]] = {}
    # グループIDとグループ名のマッピング (ソート用)
    group_id_to_name = {g.id: g.name for g in groups}
    
    # グループをorder順でソート
    sorted_groups = sorted(groups, key=lambda g: (group_orders.get(g.id, float('inf')), g.id or 9999))
    sorted_group_names = [str(g.name) for g in sorted_groups]

    # ユーザー種別IDと名前のマッピング (ソート用)
    user_type_id_to_name = {ut.id: ut.name for ut in user_types}
    # ユーザー種別IDとorderのマッピング (ソート用)
    user_type_id_mapping = {}
    user_type_info_mapping = {}  # 社員種別名 -> (order, id) のマッピング

    # 全勤怠データを再度ループし、グループ主キーのデータ構造を構築します。
    for location_name, users_list in attendance_data.items():
        # 対応する Location オブジェクトを探す
        matched_loc = next((loc for loc in location_objects if str(loc.name) == location_name), None)
        location_id = int(matched_loc.id) if matched_loc else None
        color_info = get_location_color_classes(location_id)
        location_text_class = color_info.get("text_class", "")
        location_bg_class = color_info.get("bg_class", "")

        for user_data in users_list:
            # ユーザーデータに必要な情報を追加します。
            user_data["location_name"] = location_name
            user_data["location_text_class"] = location_text_class # テキストクラスを追加
            user_data["location_bg_class"] = location_bg_class   # 背景クラスを追加

            user_obj = user.get(db, id=user_data["user_id"])
            if not user_obj:
                continue

            group_obj = groups_map.get(user_obj.group_id)
            group_name = str(group_obj.name) if group_obj else "未分類"

            # 社員種別情報を取得し、ソート用のIDマッピングも更新します。
            user_type_name = "未分類"
            user_type_id = 9999
            user_type_order = 9999
            if user_obj.user_type_id in user_types_map:
                user_type_obj = user_types_map[user_obj.user_type_id]
                user_type_name = str(user_type_obj.name)
                user_type_id = int(user_type_obj.id)
                user_type_order = int(user_type_obj.order) if user_type_obj.order is not None else 9999
                user_type_id_mapping[user_type_name] = user_type_id
                user_type_info_mapping[user_type_name] = (user_type_order, user_type_id, user_type_name)

            # グループキーの辞書が存在しない場合は初期化します。
            if group_name not in organized_by_group:
                organized_by_group[group_name] = {
                    "user_types": set(), # このグループに含まれる社員種別名のセット
                    "user_types_data": {}, # 社員種別名をキーとするユーザーリストの辞書
                    "group_id": int(user_obj.group_id) if user_obj.group_id is not None else 9999,
                    "group_order": group_orders.get(user_obj.group_id, float('inf')) # groupのorder情報を追加
                }

            organized_by_group[group_name]["user_types"].add(user_type_name)

            # 社員種別キーのリストが存在しない場合は初期化します。
            if user_type_name not in organized_by_group[group_name]["user_types_data"]:
                organized_by_group[group_name]["user_types_data"][user_type_name] = []

            organized_by_group[group_name]["user_types_data"][user_type_name].append(user_data)

    # 各グループ内の社員種別リストを、社員種別のorder、次にIDに基づいてソートします。
    for group_name in organized_by_group:
        sorted_user_types = sorted(
            list(organized_by_group[group_name]["user_types"]),
            key=lambda ut: user_type_info_mapping.get(ut, (9999, 9999, ut))
        )
        organized_by_group[group_name]["user_types"] = sorted_user_types

    # ソートキー取得用のヘルパー関数
    def get_group_sort_key(item: tuple[str, Dict[str, Any]]) -> tuple:
        group_data = item[1]
        if isinstance(group_data, dict):
            # まず order でソート、次に group_id でソート
            return (group_data.get("group_order", float('inf')), group_data.get("group_id", 9999))
        logger.warning(f"Unexpected type for group data: {type(group_data)} in item: {item}")
        return (float('inf'), 9999) # Default sort value for unexpected types

    # 最終的なグループ主キーの辞書を、グループのorderに基づいてソートします。
    sorted_organized_by_group = dict(sorted(
        organized_by_group.items(),
        key=get_group_sort_key # 新しいヘルパー関数を使用
    ))

    # この日に勤怠データが存在するかどうかのフラグを設定します。
    has_data = bool(attendance_data) and any(len(users) > 0 for users in attendance_data.values())

    # テンプレートに渡すコンテキストを作成します。
    context = {
        "request": request,
        "date_str": day,
        "date_jp": format_date_jp(parse_date(day)),
        "organized_data": organized_data, # 勤怠種別主キーデータ (使用箇所があれば更新が必要)
        "locations": locations_for_template, # 更新された勤怠種別リスト
        "organized_by_group": sorted_organized_by_group, # グループ主キーデータ (テンプレートで使用)
        "sorted_group_names": sorted_group_names, # ソート済みグループ名リスト
        "has_data": has_data,
        "attendance_data": attendance_data, # 加工前の勤怠データ
        "target_date": day
    }

    return templates.TemplateResponse(
        "components/top/day_detail.html", context
    ) 
