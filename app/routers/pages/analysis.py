"""
勤怠集計ページエンドポイント
================

勤怠集計に関連するルートハンドラー
"""

from typing import Any, Optional, Dict, List, Tuple
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.db.session import get_db

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/analysis", response_class=HTMLResponse)
def get_analysis_page(
    request: Request, 
    month: Optional[str] = None, 
    year: Optional[int] = None,
    detail_location_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Any:
    """勤怠集計ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        year: 年（指定がある場合は年ベースの集計表示）
        detail_location_id: 詳細表示する勤怠種別ID（従来の詳細表示用、現在は使用されない）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされた勤怠集計HTML
    """
    try:
        # 年ベースの表示か月ベースの集計表示かを判定
        is_year_mode = year is not None
        
        if is_year_mode:
            # 年ベースの集計表示（最初は現在月のデータで代用）
            from datetime import datetime
            current_date = datetime.now()
            current_month_str = f"{year}-{current_date.month:02d}"
            
            # 年度用のダミーデータを作成（とりあえず現在月のデータを使用）
            analysis_data = attendance.get_attendance_analysis_data(db, month=current_month_str)
            
            # 年度選択用の情報を準備
            current_year = year
            year_options = list(range(current_year - 5, current_year + 2))
            
            # グループと社員種別の情報を取得してソート用の情報を準備
            from app.crud.group import group as group_crud
            from app.crud.user_type import user_type as user_type_crud
            from app.crud.location import location as location_crud
            
            groups = group_crud.get_multi(db)
            user_types = user_type_crud.get_multi(db)
            locations = location_crud.get_multi(db)
            
            # グループのソート情報を作成
            year_group_sort_info: Dict[str, Tuple[int, int]] = {}
            for group in groups:
                year_group_sort_info[str(group.name)] = (int(group.order or 999), int(group.id))
            
            # 社員種別のソート情報を作成
            year_user_type_sort_info: Dict[str, Tuple[int, int]] = {}
            for user_type in user_types:
                year_user_type_sort_info[str(user_type.name)] = (int(user_type.order or 999), int(user_type.id))
            
            # 勤怠種別を分類→順序でソート
            sorted_locations = sorted(locations, key=lambda x: (str(x.category or ""), int(x.order or 999), int(x.id)))
            
            # analysis_dataのlocationsを順序付きに置き換え
            analysis_data["locations"] = sorted_locations
            
            # 年度期間の詳細データを取得
            location_details = {}
            for location in sorted_locations:
                # 年度期間の開始日と終了日を計算
                from datetime import date
                fiscal_start = date(year, 4, 1)
                fiscal_end = date(year + 1, 3, 31)
                
                # 対象期間・勤怠種別の勤怠データを取得
                from sqlalchemy import and_
                attendances = (
                    db.query(attendance.model)
                    .filter(
                        and_(
                            attendance.model.date >= fiscal_start,
                            attendance.model.date <= fiscal_end,
                            attendance.model.location_id == location.id
                        )
                    )
                    .order_by(attendance.model.date)
                    .all()
                )
                
                # ユーザー別に勤怠日付をグループ化
                location_user_data: Dict[str, List[Dict[str, str]]] = {}
                for att in attendances:
                    user_id_str = str(att.user_id)
                    if user_id_str not in location_user_data:
                        location_user_data[user_id_str] = []
                    location_user_data[user_id_str].append({
                        "date_str": att.date.strftime("%Y-%m-%d"),
                        "date_jp": f"{att.date.month}月{att.date.day}日",
                        "date_mmdd": att.date.strftime("%m/%d"),
                        "date_simple": f"{att.date.month}/{att.date.day}",
                        "note": str(att.note or "")
                    })
                
                location_details[location.id] = location_user_data
            
            # グループ別にユーザーを整理
            year_grouped_users: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
            year_group_user_types: Dict[str, List[str]] = {}
            
            for user_id, user_info in analysis_data["users"].items():
                group_name = user_info["group_name"] or "未分類"
                if group_name not in year_grouped_users:
                    year_grouped_users[group_name] = []
                    year_group_user_types[group_name] = []
                year_grouped_users[group_name].append((user_id, user_info))
            
            # 各グループ内でユーザーを社員種別順にソート
            for group_name in year_grouped_users:
                year_grouped_users[group_name].sort(
                    key=lambda x: year_user_type_sort_info.get(str(x[1]["user_type_name"] or ""), (999, 999))
                )
                
                # このグループの社員種別リストを作成（順序付き、重複なし）
                user_types_in_group = []
                seen_types = set()
                for user_id, user_info in year_grouped_users[group_name]:
                    user_type_name = user_info["user_type_name"] or "未分類"
                    if user_type_name not in seen_types:
                        user_types_in_group.append(user_type_name)
                        seen_types.add(user_type_name)
                year_group_user_types[group_name] = user_types_in_group
            
            # グループ名をorder順にソート
            year_sorted_group_names = sorted(
                year_grouped_users.keys(),
                key=lambda x: year_group_sort_info.get(str(x), (999, 999))
            )
            
            # 月選択用の情報を準備
            month_options = [f"{m:02d}" for m in range(1, 13)]
            
            # 年度データ用の表示名を更新
            analysis_data["month"] = f"{year}年度"
            analysis_data["month_name"] = f"{year}年度"
            
            context = {
                "request": request,
                "analysis_data": analysis_data,
                "detail_data": None,
                "is_detail_mode": False,
                "is_year_mode": True,
                "current_month": None,
                "current_year": current_year,
                "year_options": year_options,
                "month_options": month_options,
                "prev_month": None,
                "next_month": None,
                "grouped_users": year_grouped_users,
                "sorted_group_names": year_sorted_group_names,
                "group_user_types": year_group_user_types,
                "location_details": location_details
            }
            
        else:
            # 月ベースの集計表示
            analysis_data = attendance.get_attendance_analysis_data(db, month=month)
            
            # 月切り替え用の前月・次月を計算
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            
            current_month = analysis_data["month"]
            year_num, month_num = map(int, current_month.split('-'))
            current_date = datetime(year_num, month_num, 1)
            
            prev_month_date = current_date - relativedelta(months=1)
            next_month_date = current_date + relativedelta(months=1)
            
            prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"
            next_month = f"{next_month_date.year}-{next_month_date.month:02d}"
            
            # グループと社員種別、勤怠種別の情報を取得してソート用の情報を準備
            from app.crud.group import group as group_crud
            from app.crud.user_type import user_type as user_type_crud
            from app.crud.location import location as location_crud
            
            groups = group_crud.get_multi(db)
            user_types = user_type_crud.get_multi(db)
            locations = location_crud.get_multi(db)
            
            # グループのソート情報を作成
            summary_group_sort_info: Dict[str, Tuple[int, int]] = {}
            for group in groups:
                summary_group_sort_info[str(group.name)] = (int(group.order or 999), int(group.id))
            
            # 社員種別のソート情報を作成
            month_user_type_sort_info: Dict[str, Tuple[int, int]] = {}
            for user_type in user_types:
                month_user_type_sort_info[str(user_type.name)] = (int(user_type.order or 999), int(user_type.id))
            
            # 勤怠種別を分類→順序でソート
            sorted_locations = sorted(locations, key=lambda x: (str(x.category or ""), int(x.order or 999), int(x.id)))
            
            # analysis_dataのlocationsを順序付きに置き換え
            analysis_data["locations"] = sorted_locations
            
            # 各勤怠種別の詳細データを取得（月ベース）
            location_details = {}
            for location in sorted_locations:
                # 月の開始日と終了日を計算
                from datetime import date
                import calendar
                first_day = date(year_num, month_num, 1)
                last_day = date(year_num, month_num, calendar.monthrange(year_num, month_num)[1])
                
                # 対象期間・勤怠種別の勤怠データを取得
                from sqlalchemy import and_
                attendances = (
                    db.query(attendance.model)
                    .filter(
                        and_(
                            attendance.model.date >= first_day,
                            attendance.model.date <= last_day,
                            attendance.model.location_id == location.id
                        )
                    )
                    .order_by(attendance.model.date)
                    .all()
                )
                
                # ユーザー別に勤怠日付をグループ化
                month_location_user_data: Dict[str, List[Dict[str, str]]] = {}
                for att in attendances:
                    user_id_str = str(att.user_id)
                    if user_id_str not in month_location_user_data:
                        month_location_user_data[user_id_str] = []
                    month_location_user_data[user_id_str].append({
                        "date_str": att.date.strftime("%Y-%m-%d"),
                        "date_jp": f"{att.date.month}月{att.date.day}日",
                        "date_mmdd": att.date.strftime("%m/%d"),
                        "date_simple": f"{att.date.month}/{att.date.day}",
                        "note": str(att.note or "")
                    })
                
                location_details[location.id] = month_location_user_data
            
            # グループ別にユーザーを整理
            summary_grouped_users: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
            month_group_user_types: Dict[str, List[str]] = {}
            
            for user_id, user_info in analysis_data["users"].items():
                group_name = user_info["group_name"] or "未分類"
                if group_name not in summary_grouped_users:
                    summary_grouped_users[group_name] = []
                    month_group_user_types[group_name] = []
                summary_grouped_users[group_name].append((user_id, user_info))
            
            # 各グループ内でユーザーを社員種別順にソート
            for group_name in summary_grouped_users:
                summary_grouped_users[group_name].sort(
                    key=lambda x: month_user_type_sort_info.get(str(x[1]["user_type_name"] or ""), (999, 999))
                )
                
                # このグループの社員種別リストを作成（順序付き、重複なし）
                user_types_in_group = []
                seen_types = set()
                for user_id, user_info in summary_grouped_users[group_name]:
                    user_type_name = user_info["user_type_name"] or "未分類"
                    if user_type_name not in seen_types:
                        user_types_in_group.append(user_type_name)
                        seen_types.add(user_type_name)
                month_group_user_types[group_name] = user_types_in_group
            
            # グループ名をorder順にソート
            summary_sorted_group_names = sorted(
                summary_grouped_users.keys(),
                key=lambda x: summary_group_sort_info.get(str(x), (999, 999))
            )
            
            # 月・年選択用の情報を準備
            current_year = year_num
            year_options = list(range(current_year - 5, current_year + 2))
            month_options = [f"{m:02d}" for m in range(1, 13)]
            
            context = {
                "request": request,
                "analysis_data": analysis_data,
                "detail_data": None,
                "is_detail_mode": False,
                "is_year_mode": False,
                "current_month": analysis_data["month"],
                "current_year": current_year,
                "year_options": year_options,
                "month_options": month_options,
                "prev_month": prev_month,
                "next_month": next_month,
                "grouped_users": summary_grouped_users,
                "sorted_group_names": summary_sorted_group_names,
                "group_user_types": month_group_user_types,
                "location_details": location_details
            }
        
        return templates.TemplateResponse("pages/analysis.html", context)
        
    except Exception as e:
        logger.error(f"勤怠集計ページ表示中にエラーが発生しました: {str(e)}", exc_info=True)
        # エラー時は空のデータで表示
        context = {
            "request": request,
            "analysis_data": {
                "month": month or "",
                "month_name": "エラー",
                "users": {},
                "locations": [],
                "summary": {"total_users": 0, "total_attendance_days": 0}
            },
            "detail_data": None,
            "is_detail_mode": False,
            "is_year_mode": False,
            "current_month": month or "",
            "current_year": None,
            "year_options": [],
            "month_options": [],
            "prev_month": "",
            "next_month": "",
            "grouped_users": {},
            "sorted_group_names": [],
            "group_user_types": {},
            "location_details": {}
        }
        return templates.TemplateResponse("pages/analysis.html", context) 