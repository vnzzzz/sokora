"""勤怠集計のread modelを組み立てるservice。"""

import calendar as calendar_module
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud


def get_attendance_analysis_data(
    db: Session,
    *,
    month: Optional[str] = None,
    fiscal_year: Optional[int] = None,
) -> Dict[str, Any]:
    """月次または年度の勤怠集計coreとなるread modelを構築する。

    ``fiscal_year`` が指定された場合は4月1日〜翌3月31日の年度集計を優先し、``month``
    は使用しない。年度指定が無い場合は``YYYY-MM``の月次集計とし、month未指定時だけ
    current monthを採用する。

    user/location/attendanceを順に取得してPython上で集計する。PostgreSQL READ COMMITTEDでは
    各queryが異なるcommitted stateを観測し得るため、先に取得したuser/location集合をその
    responseのprojection boundaryとする。後続attendance queryだけが新しいmaster参照rowを
    観測した場合は現在responseから除外し、commit後に開始する次readで反映する。

    返却shapeはpresentation serviceがgroup/category/orderを再編成するためのraw read modelで
    あり、このfunctionはDB mutationやprocess-local result cacheを持たない。
    """
    if fiscal_year is not None:
        period_mode = "fiscal_year"
        start_date = date(fiscal_year, 4, 1)
        end_date = date(fiscal_year + 1, 3, 31)
        period_label = f"{fiscal_year}年度"
        month_value: Optional[str] = None
    else:
        current_date = datetime.now()
        if month is None:
            month = f"{current_date.year}-{current_date.month:02d}"
        year, month_num = map(int, month.split("-"))
        period_mode = "month"
        start_date = date(year, month_num, 1)
        end_date = date(
            year,
            month_num,
            calendar_module.monthrange(year, month_num)[1],
        )
        period_label = f"{year}年{month_num}月"
        month_value = month

    users_data = crud.user.get_all_users_with_details(db)
    locations = crud.location.get_multi(db)
    locations_sorted = sorted(
        locations,
        key=lambda item: (str(item.category or ""), item.order or 999, item.id),
    )
    attendances = crud.attendance.list_for_period(
        db,
        start_date=start_date,
        end_date=end_date,
    )

    user_analysis: Dict[str, Dict[str, Any]] = {}
    location_totals = {
        int(location.id): 0 for location in locations_sorted if location.id is not None
    }
    location_details: Dict[int, Dict[str, List[Dict[str, Any]]]] = {
        int(location.id): {} for location in locations_sorted if location.id is not None
    }

    visible_user_ids = {str(user_id) for _, user_id, _, _ in users_data}
    visible_location_ids = set(location_totals)

    attendances_by_user: Dict[str, list[Any]] = {}
    for attendance in attendances:
        user_id = str(attendance.user_id)
        location_id = int(attendance.location_id)

        # READ COMMITTEDではmaster query後のcommitをattendance queryだけが観測し得る。
        # 先行master readに無い参照rowはこのresponseへ混ぜず、次requestで完全に反映する。
        if user_id not in visible_user_ids or location_id not in visible_location_ids:
            continue

        attendances_by_user.setdefault(user_id, []).append(attendance)

    for user_name, user_id, group_name, user_type_name in users_data:
        user_attendances = attendances_by_user.get(str(user_id), [])
        location_counts = {
            int(location.id): 0
            for location in locations_sorted
            if location.id is not None
        }
        location_dates: Dict[int, List[Dict[str, Any]]] = {
            int(location.id): []
            for location in locations_sorted
            if location.id is not None
        }

        for attendance in user_attendances:
            location_id = int(attendance.location_id)
            location_counts[location_id] += 1
            location_totals[location_id] += 1
            location_dates[location_id].append(
                {
                    "date_str": attendance.date.strftime("%Y-%m-%d"),
                    "date_jp": f"{attendance.date.month}月{attendance.date.day}日",
                    "date_mmdd": attendance.date.strftime("%m/%d"),
                    "date_simple": f"{attendance.date.month}/{attendance.date.day}",
                    "note": attendance.note or "",
                }
            )

        for location_id, dates in location_dates.items():
            if dates:
                dates.sort(key=lambda item: item["date_str"])
                location_details[location_id][str(user_id)] = dates

        user_analysis[str(user_id)] = {
            "user_name": user_name,
            "group_name": group_name,
            "user_type_name": user_type_name,
            "location_counts": location_counts,
            "location_dates": location_dates,
            "total_days": sum(location_counts.values()),
        }

    locations_info: List[SimpleNamespace] = []
    for location in locations_sorted:
        if location.id is None:
            continue
        location_id = int(location.id)
        locations_info.append(
            SimpleNamespace(
                id=location.id,
                name=location.name,
                category=location.category,
                order=location.order,
                total_days=location_totals[location_id],
            )
        )

    group_summary: Dict[str, Dict[str, Any]] = {}
    for _, user_id, group_name, _ in users_data:
        group_key = group_name or "未分類"
        if group_key not in group_summary:
            group_summary[group_key] = {
                "location_counts": {
                    int(location.id): 0
                    for location in locations_sorted
                    if location.id is not None
                },
                "total_days": 0,
            }
        user_counts = user_analysis.get(str(user_id), {}).get("location_counts", {})
        for location_id, count in user_counts.items():
            group_summary[group_key]["location_counts"][location_id] += count
            group_summary[group_key]["total_days"] += count

    return {
        "month": month_value or "",
        "month_name": period_label,
        "period": {
            "mode": period_mode,
            "label": period_label,
            "start": start_date,
            "end": end_date,
            "fiscal_year": fiscal_year,
            "month": month_value,
        },
        "users": user_analysis,
        "locations": locations_info,
        "group_summary": group_summary,
        "location_details": location_details,
        "summary": {
            "total_users": len(user_analysis),
            "total_attendance_days": sum(location_totals.values()),
            "location_totals": location_totals,
        },
    }
