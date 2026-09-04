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
    """CSV projection用に``user_id_YYYY-MM-DD``をkeyとする勤怠種別mappingを返す。

    optionalな開始/終了日はpersistence queryへそのまま渡し、範囲外rowをservice側で再filter
    しない。1ユーザー1日1勤怠というDB unique contractを前提に1 keyへ1 valueだけを持つ。
    export readは共有DBのcurrent stateから毎回構築し、process-local cacheを作らない。
    """
    rows = crud.attendance.list_export_rows(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        f"{row.user_id}_{row.date.strftime('%Y-%m-%d')}": str(row.location_name)
        for row in rows
    }
