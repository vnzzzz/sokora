"""勤怠集計画面の日別明細へ現在のfilter条件を適用する。"""

from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services import calendar_read_service


def get_filtered_day_detail_view_model(
    db: Session,
    *,
    day: date,
    selected_location_ids: Optional[list[int]] = None,
    group_name: Optional[str] = None,
    user_type_name: Optional[str] = None,
) -> calendar_read_service.DayDetailViewModel:
    """汎用calendar detailを再利用し、analysis filterと一致する行だけを返す。"""
    view_model = calendar_read_service.get_day_detail_view_model(db, day=day)

    selected_ids: Optional[set[int]] = None
    if selected_location_ids is not None:
        selected_ids = {int(location_id) for location_id in selected_location_ids}

    normalized_group_name = (group_name or "").strip() or None
    normalized_user_type_name = (user_type_name or "").strip() or None
    filtered_groups: dict[str, dict[str, Any]] = {}

    for current_group_name, group_data in view_model["organized_by_group"].items():
        if (
            normalized_group_name is not None
            and current_group_name != normalized_group_name
        ):
            continue

        filtered_user_types: list[str] = []
        filtered_user_type_data: dict[str, list[dict[str, Any]]] = {}
        for current_user_type in group_data["user_types"]:
            if (
                normalized_user_type_name is not None
                and current_user_type != normalized_user_type_name
            ):
                continue

            users = list(group_data["user_types_data"].get(current_user_type, []))
            if selected_ids is not None:
                users = [
                    user
                    for user in users
                    if int(user["location_id"]) in selected_ids
                ]
            if not users:
                continue

            filtered_user_types.append(current_user_type)
            filtered_user_type_data[current_user_type] = users

        if not filtered_user_types:
            continue

        filtered_group_data = dict(group_data)
        filtered_group_data["user_types"] = filtered_user_types
        filtered_group_data["user_types_data"] = filtered_user_type_data
        filtered_groups[current_group_name] = filtered_group_data

    return {
        **view_model,
        "organized_by_group": filtered_groups,
        "has_data": bool(filtered_groups),
    }
