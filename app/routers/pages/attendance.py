"""
勤怠管理ページエンドポイント
----------------

勤怠登録・管理ページに関連するルートハンドラー
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import date, timedelta
import calendar
import operator

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.attendance import attendance
from app.crud.group import group
from app.crud.location import location as location_crud
from app.crud.calendar import calendar_crud
from app.crud.user import user
from app.crud.user_type import user_type
from app.db.session import get_db
from app.models.location import Location
from app.models.attendance import Attendance as AttendanceModel
from app.utils.calendar_utils import build_calendar_data, parse_month, get_current_month_formatted, format_date_jp
from app.utils.ui_utils import get_location_color_classes

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

    # DBからカレンダー構築に必要なデータを取得
    try:
        year, month_num = parse_month(month)
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

        attendances_for_cal = calendar_crud.get_month_attendances(db, first_day=first_day, last_day=last_day)
        attendance_counts_for_cal = calendar_crud.get_month_attendance_counts(db, first_day=first_day, last_day=last_day)
        location_types_unsorted_for_cal = location_crud.get_all_locations(db)
        location_types_for_cal = sorted(location_types_unsorted_for_cal)

        # 指定された月のカレンダーデータを構築します。
        logger.debug(f"カレンダーデータ構築: {month}")
        calendar_data = build_calendar_data(
            month=month,
            attendances=attendances_for_cal,
            attendance_counts=attendance_counts_for_cal,
            location_types=location_types_for_cal
        )
    except ValueError as e:
        logger.error(f"月解析エラー ({month}): {e}")
        calendar_data = None # エラー発生
    except Exception as e:
        logger.error(f"カレンダーデータ構築中にエラー ({month}): {e}", exc_info=True)
        calendar_data = None # エラー発生

    # カレンダーデータの取得に失敗した場合、現在の月にフォールバックします。
    if not calendar_data or "weeks" not in calendar_data:
        logger.error(f"カレンダーデータの構築に失敗: {month}")
        month = get_current_month_formatted()
        # 再度データを取得して構築（エラーハンドリングは簡略化）
        try:
            year, month_num = parse_month(month)
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
            attendances_for_cal = calendar_crud.get_month_attendances(db, first_day=first_day, last_day=last_day)
            attendance_counts_for_cal = calendar_crud.get_month_attendance_counts(db, first_day=first_day, last_day=last_day)
            location_types_unsorted_for_cal = location_crud.get_all_locations(db)
            location_types_for_cal = sorted(location_types_unsorted_for_cal)
            calendar_data = build_calendar_data(
                month=month,
                attendances=attendances_for_cal,
                attendance_counts=attendance_counts_for_cal,
                location_types=location_types_for_cal
            )
        except:
            logger.exception(f"フォールバック時のカレンダーデータ構築にも失敗: {month}")
            # さらにエラーなら空データを設定
            calendar_data = {"weeks": [], "month_name": "エラー", "prev_month": month, "next_month": month}

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
        user_obj = user.get(db, id=user_id)
        if user_obj:
            users.append((user_name, user_id, user_type_id, user_obj))

    # グループ情報をIDをキーとする辞書として取得します。
    groups = group.get_multi(db)
    groups_map = {g.id: g for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.id: ut for ut in user_types}

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

    # 利用可能な全勤務場所を取得します。（オブジェクトのリストとして）
    location_objects_unsorted: List[Location] = location_crud.get_multi(db)
    # IDでソートした Location オブジェクトのリストをテンプレートに渡す
    location_objects = sorted(location_objects_unsorted, key=operator.attrgetter('id'))

    # 勤務場所名に対応するCSSクラス情報 (テキストと背景) を生成します。
    location_styles: Dict[str, Dict[str, str]] = {}
    for loc in location_objects:
        location_styles[str(loc.name)] = get_location_color_classes(int(loc.id))

    # JavaScript用に Location ID と Name のマッピングを作成
    location_data_for_js = {loc.id: str(loc.name) for loc in location_objects}

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
        "location_objects": location_objects, # オブジェクトリストを渡す
        "location_styles": location_styles, # 更新されたスタイル辞書
        "location_data_for_js": location_data_for_js, # JS 用データ
        "user_attendances": user_attendances,
        "user_attendance_locations": user_attendance_locations,
        "calendar_day_count": calendar_day_count,
        "search_query": search_query,
    }

    # 現在選択中の月 (YYYY-MM) をコンテキストに追加
    context["current_month"] = month

    # HTMXリクエストの場合、勤怠テーブル部分のみをレンダリングして返します。
    if request.headers.get("HX-Request") == "true":
        logger.debug("HTMXリクエストを検出。部分テンプレートを返します。")
        return templates.TemplateResponse(
            "pages/attendance/attendance_calendar.html", context,
            headers={"HX-Reswap": "innerHTML"} # HTMXに入れ替え方法を指定
        )

    # 通常のGETリクエストの場合、完全なHTMLページをレンダリングして返します。
    logger.debug("通常リクエスト。完全なページを返します。")
    return templates.TemplateResponse(
        "pages/attendance/index.html", context
    )


@router.get("/pages/attendances/modal/{user_id}/{date_str}", response_class=HTMLResponse)
def get_attendance_modal(
    request: Request,
    user_id: str,
    date_str: str, # パスパラメータは YYYY-MM-DD 形式を期待
    db: Session = Depends(get_db),
) -> Any:
    """指定されたユーザーと日付の勤怠編集モーダルを返します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集対象のユーザーID
        date_str: 編集対象の日付（YYYY-MM-DD形式）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    logger.info(f"勤怠モーダルリクエスト受信: User={user_id}, Date={date_str}")
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.warning(f"無効な日付形式: {date_str}")
        # エラーを示す空のコンテナを返すか、エラーメッセージを含むHTMLを返す
        return HTMLResponse(content="", status_code=status.HTTP_400_BAD_REQUEST)

    user_obj = user.get(db, id=user_id)
    if not user_obj:
        logger.warning(f"ユーザーが見つかりません: {user_id}")
        return HTMLResponse(content="", status_code=status.HTTP_404_NOT_FOUND)

    # 既存の勤怠データを取得 (CRUD関数名を修正)
    attendance_obj: Optional[AttendanceModel] = attendance.get_by_user_and_date(db, user_id=user_id, date=target_date)
    attendance_id = attendance_obj.id if attendance_obj else None
    current_location_id = attendance_obj.location_id if attendance_obj else None

    # 全勤務場所を取得
    locations: List[Location] = sorted(location_crud.get_multi(db), key=operator.attrgetter('id'))

    # モーダルテンプレートに必要なコンテキストを作成
    context = {
        "request": request,
        "user_id": user_id,
        "user_name": str(user_obj.username),
        "date": date_str,
        "formatted_date": format_date_jp(target_date), # 日本語形式の日付 (calendar_utilsからインポート)
        "attendance_id": attendance_id,
        "current_location_id": current_location_id,
        "locations": locations,
    }
    logger.debug(f"モーダルコンテキスト: {context}")

    # モーダルコンポーネントをレンダリング (テンプレートパスを修正)
    return templates.TemplateResponse(
        "components/attendance/_attendance_modal.html", # _content.html を削除
        context,
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