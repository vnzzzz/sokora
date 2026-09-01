"""勤怠read projectionをpersistence queryから組み立てる。"""

from datetime import date
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app import crud


def get_attendance_data_for_csv(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, str]:
    """CSV用に user_id + date から勤怠種別名へのmappingを返す。"""
    rows = crud.attendance.list_export_rows(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        f"{row.user_id}_{row.date.strftime('%Y-%m-%d')}": str(row.location_name)
        for row in rows
    }
