"""
勤怠集計ページエンドポイント
================

勤怠集計に関連するルートハンドラー
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.services import attendance_analysis_service

router = APIRouter(prefix="/analysis", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_analysis_page(
    request: Request,
    month: Optional[str] = None,
    year: Optional[int] = None,
    detail_location_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """勤怠集計ページを表示します。"""
    try:
        from datetime import datetime

        current_date = datetime.now()
        query_params = dict(request.query_params)
        mode_param = query_params.get("mode")
        fiscal_default = (
            current_date.year if current_date.month >= 4 else current_date.year - 1
        )

        is_year_mode = year is not None or mode_param == "year"
        target_fiscal_year = year if year is not None else fiscal_default

        if is_year_mode:
            analysis_data = attendance_analysis_service.get_attendance_analysis_data(
                db, fiscal_year=target_fiscal_year
            )
        else:
            month_value = month or f"{current_date.year}-{current_date.month:02d}"
            analysis_data = attendance_analysis_service.get_attendance_analysis_data(
                db, month=month_value
            )

        prev_month = next_month = None
        if analysis_data["period"]["month"]:
            from dateutil.relativedelta import relativedelta

            current_month = analysis_data["period"]["month"]
            year_num, month_num = map(int, current_month.split("-"))
            current_date_for_nav = datetime(year_num, month_num, 1)
            prev_month_date = current_date_for_nav - relativedelta(months=1)
            next_month_date = current_date_for_nav + relativedelta(months=1)
            prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"
            next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

        from app.crud.group import group as group_crud
        from app.crud.user_type import user_type as user_type_crud

        groups = group_crud.get_multi(db)
        user_types = user_type_crud.get_multi(db)

        group_sort_info: Dict[str, Tuple[int, int]] = {}
        for group in groups:
            group_sort_info[str(group.name)] = (int(group.order or 999), int(group.id))

        user_type_sort_info: Dict[str, Tuple[int, int]] = {}
        for user_type in user_types:
            user_type_sort_info[str(user_type.name)] = (
                int(user_type.order or 999),
                int(user_type.id),
            )

        grouped_users: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        group_user_types: Dict[str, List[str]] = {}

        for user_id, user_info in analysis_data["users"].items():
            group_name = user_info["group_name"] or "未分類"
            if group_name not in grouped_users:
                grouped_users[group_name] = []
                group_user_types[group_name] = []
            grouped_users[group_name].append((user_id, user_info))

        for group_name in grouped_users:
            grouped_users[group_name].sort(
                key=lambda item: user_type_sort_info.get(
                    str(item[1]["user_type_name"] or ""), (999, 999)
                )
            )
            user_types_in_group: List[str] = []
            seen_types = set()
            for _, user_info in grouped_users[group_name]:
                user_type_name = user_info["user_type_name"] or "未分類"
                if user_type_name not in seen_types:
                    user_types_in_group.append(user_type_name)
                    seen_types.add(user_type_name)
            group_user_types[group_name] = user_types_in_group

        sorted_group_names = sorted(
            grouped_users.keys(), key=lambda item: group_sort_info.get(str(item), (999, 999))
        )

        month_options = [f"{month_num:02d}" for month_num in range(1, 13)]
        year_options = list(range(fiscal_default - 3, fiscal_default + 4))
        current_month_value = (
            analysis_data["period"]["month"]
            or f"{current_date.year}-{current_date.month:02d}"
        )

        context: Dict[str, Any] = {
            "request": request,
            "analysis_data": analysis_data,
            "detail_data": None,
            "is_detail_mode": False,
            "is_year_mode": analysis_data["period"]["mode"] == "fiscal_year",
            "current_month": current_month_value,
            "current_year": analysis_data["period"]["fiscal_year"] or fiscal_default,
            "year_options": year_options,
            "month_options": month_options,
            "prev_month": prev_month,
            "next_month": next_month,
            "grouped_users": grouped_users,
            "sorted_group_names": sorted_group_names,
            "group_user_types": group_user_types,
            "location_details": analysis_data.get("location_details", {}),
            "group_summary": analysis_data.get("group_summary", {}),
        }
        return templates.TemplateResponse("pages/analysis.html", context)
    except Exception as exc:
        logger.error(
            "勤怠集計ページ表示中にエラーが発生しました: %s", exc, exc_info=True
        )
        error_context: Dict[str, Any] = {
            "request": request,
            "analysis_data": {
                "month": month or "",
                "month_name": "エラー",
                "period": {
                    "mode": "error",
                    "label": "エラー",
                    "start": None,
                    "end": None,
                    "fiscal_year": None,
                    "month": month or "",
                },
                "users": {},
                "locations": [],
                "group_summary": {},
                "location_details": {},
                "summary": {"total_users": 0, "total_attendance_days": 0},
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
            "location_details": {},
            "group_summary": {},
        }
        return templates.TemplateResponse("pages/analysis.html", error_context)
