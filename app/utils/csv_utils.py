"""勤怠データをCSV形式へ変換するutility。"""

import calendar
from datetime import date, datetime
from typing import Dict, Generator, List, Optional, Tuple

from dateutil.relativedelta import relativedelta  # type: ignore
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.user import user as crud_user
from app.services import attendance_read_service


def get_available_months(num_months: int = 12) -> List[Dict[str, str]]:
    """現在月から遡ってCSV出力対象月の選択肢を返す。

    Args:
        num_months: 現在月を含めて返す月数。

    Returns:
        `value=YYYY-MM`と日本語labelを持つ月optionのlist。
    """
    today = datetime.now().date()
    months = []
    for index in range(num_months):
        target_date = today - relativedelta(months=index)
        months.append(
            {
                "value": target_date.strftime("%Y-%m"),
                "label": f"{target_date.year}年{target_date.month}月",
            }
        )
    return months


def get_date_range_for_month(month: str) -> Tuple[date, date]:
    """`YYYY-MM`からinclusiveな月初・月末を返す。

    Args:
        month: 対象月。`YYYY-MM`形式。

    Returns:
        月初日と月末日のtuple。

    Raises:
        ValueError: monthが`YYYY-MM`として解釈できない場合。
    """
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_int = int(month_str)
    start_date = date(year, month_int, 1)
    _, last_day = calendar.monthrange(year, month_int)
    return start_date, date(year, month_int, last_day)


def _generate_date_headers(month: Optional[str] = None) -> List[str]:
    """CSV用の日付headerを生成する。

    Args:
        month: `YYYY-MM`形式の対象月。未指定時は直近90日を対象にする。

    Returns:
        `YYYY/MM/DD`形式の日付header list。

    Raises:
        ValueError: month形式が不正な場合。
    """
    today = date.today()
    if month:
        start_date, end_date = get_date_range_for_month(month)
        current_date = start_date
        date_headers = []
        while current_date <= end_date:
            date_headers.append(current_date.strftime("%Y/%m/%d"))
            current_date += relativedelta(days=1)
        return date_headers

    date_headers = [
        (today - relativedelta(days=index)).strftime("%Y/%m/%d") for index in range(90)
    ]
    date_headers.sort()
    return date_headers


def generate_work_entries_csv_rows(
    db: Session,
    month: Optional[str] = None,
) -> Generator[List[str], None, None]:
    """勤怠CSVの行をstreaming用に生成する。

    Args:
        db: DB session。
        month: `YYYY-MM`形式の対象月。未指定時は直近90日を対象にする。

    Yields:
        先頭にheader、その後userごとのCSV row。

    Raises:
        ValueError: month形式が不正な場合。
    """
    date_headers = _generate_date_headers(month)
    yield ["user_name", "user_id", "group_name", "user_type", *date_headers]

    users_data = crud_user.get_all_users_with_details(db)
    if not users_data:
        logger.info("CSV生成: 対象ユーザーが見つかりませんでした。")
        return

    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    if date_headers:
        date_range_start = datetime.strptime(date_headers[0], "%Y/%m/%d").date()
        date_range_end = datetime.strptime(date_headers[-1], "%Y/%m/%d").date()

    attendance_data = attendance_read_service.get_attendance_data_for_csv(
        db,
        start_date=date_range_start,
        end_date=date_range_end,
    )

    for user_name, user_id, group_name, user_type_name in users_data:
        row_data = [
            user_name or "",
            user_id or "",
            group_name or "",
            user_type_name or "",
        ]
        for date_str_header in date_headers:
            db_date_str = datetime.strptime(date_str_header, "%Y/%m/%d").strftime(
                "%Y-%m-%d"
            )
            row_data.append(attendance_data.get(f"{user_id}_{db_date_str}", ""))
        yield row_data
