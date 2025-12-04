"""
CSV変換ユーティリティ
=================

勤怠データをCSV形式に変換するためのユーティリティ関数を提供します。
"""

from typing import Dict, List, Optional, Tuple, Generator
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta  # type: ignore
from sqlalchemy.orm import Session

from app.crud.user import user as crud_user # エイリアス変更
from app.crud.attendance import attendance as crud_attendance # エイリアス変更
from app.core.config import logger # loggerを追加

def get_available_months(num_months: int = 12) -> List[Dict[str, str]]:
    """
    利用可能な月のリストを取得します

    Args:
        num_months: 現在の月から遡って取得する月数

    Returns:
        List[Dict[str, str]]: 月情報のリスト (value, label)
    """
    today = datetime.now().date()
    months = []
    
    # 現在の月から過去num_months分の月を生成
    for i in range(num_months):
        target_date = today - relativedelta(months=i)
        value = target_date.strftime("%Y-%m")
        # 日本語の年月表記
        label = f"{target_date.year}年{target_date.month}月"
        months.append({"value": value, "label": label})
    
    return months

def get_date_range_for_month(month: str) -> Tuple[date, date]:
    """
    指定された月の日付範囲を取得します

    Args:
        month: 'YYYY-MM'形式の月文字列

    Returns:
        Tuple[date, date]: 開始日と終了日
    """
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_int = int(month_str)
    start_date = date(year, month_int, 1)
    
    # 月の最終日を取得
    _, last_day = calendar.monthrange(year, month_int)
    end_date = date(year, month_int, last_day)
    
    return start_date, end_date

def _generate_date_headers(month: Optional[str] = None) -> List[str]:
    """CSV用の日付ヘッダーリストを生成します。"""
    today = date.today()
    if month:
        start_date, end_date = get_date_range_for_month(month)
        current_date = start_date
        date_headers = []
        while current_date <= end_date:
            date_headers.append(current_date.strftime("%Y/%m/%d"))
            current_date += relativedelta(days=1)
    else:
        # 月指定がない場合はデフォルトで過去3ヶ月（約90日）とする
        # 仕様に応じて調整可能
        num_days = 90 
        date_headers = [
            (today - relativedelta(days=i)).strftime("%Y/%m/%d") 
            for i in range(num_days)
        ]
        date_headers.sort() # 日付順にソート
    return date_headers

def generate_work_entries_csv_rows(
    db: Session, month: Optional[str] = None
) -> Generator[List[str], None, None]:
    """
    勤怠データのCSV行を生成するジェネレータ。

    Args:
        db: データベースセッション
        month: 'YYYY-MM'形式の月文字列（Noneの場合はデフォルト期間）

    Yields:
        List[str]: CSVの1行を表す文字列リスト（ヘッダー行を含む）
    """
    try:
        date_headers = _generate_date_headers(month)
        headers = ["user_name", "user_id", "group_name", "user_type"] + date_headers
        yield headers # ヘッダー行をyield

        # ユーザーデータを関連情報と共に取得
        users_data = crud_user.get_all_users_with_details(db)
        if not users_data:
            logger.info("CSV生成: 対象ユーザーが見つかりませんでした。")
            return # ユーザーがいなければ終了

        # 勤怠データの日付範囲を決定
        date_range_start: Optional[date] = None
        date_range_end: Optional[date] = None
        if date_headers: # ヘッダーがあれば範囲を決定
            try:
                # ヘッダーは YYYY/MM/DD 形式
                date_range_start = datetime.strptime(date_headers[0], "%Y/%m/%d").date()
                date_range_end = datetime.strptime(date_headers[-1], "%Y/%m/%d").date()
            except (ValueError, IndexError) as e:
                logger.error(f"日付ヘッダーからの範囲決定に失敗: {e}")
                # エラーが発生した場合、範囲指定なしで取得 (あるいはエラー終了)
                pass

        # 勤怠データを一括取得
        logger.debug(f"勤怠データ取得範囲: {date_range_start} - {date_range_end}")
        attendance_data = crud_attendance.get_attendance_data_for_csv(
            db, start_date=date_range_start, end_date=date_range_end
        )
        logger.debug(f"取得した勤怠データ件数: {len(attendance_data)}")

        # 各ユーザーについて行を生成
        for user_name, user_id, group_name, user_type_name in users_data:
            row_data = [
                user_name or "",
                user_id or "",
                group_name or "",
                user_type_name or ""
            ]

            # 各日付列のデータを追加
            for date_str_header in date_headers:
                # ヘッダー形式 (YYYY/MM/DD) からDB検索用のキー形式 (YYYY-MM-DD) へ
                try:
                    db_date_str = datetime.strptime(date_str_header, "%Y/%m/%d").strftime("%Y-%m-%d")
                    user_date_key = f"{user_id}_{db_date_str}"
                    location_name = attendance_data.get(user_date_key, "")
                    row_data.append(location_name)
                except ValueError:
                    # 日付変換エラー時は空文字を追加
                    row_data.append("")

            yield row_data # データ行をyield

    except Exception as e:
        logger.error(f"CSV行生成中にエラー: {e}", exc_info=True)
        # エラーが発生した場合、エラーを示す特別な行を返すか、ログに記録して終了
        yield ["Error generating CSV data"] # エラーを示す行 (ヘッダーとは異なる列数)

# get_work_entries_csv 関数は不要になる (エンドポイントで直接ジェネレータを使うため)
# def get_work_entries_csv(...) -> bytes:
#    ... (古い実装) ... 