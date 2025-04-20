"""
CSV変換ユーティリティ
=================

勤怠データをCSV形式に変換するためのユーティリティ関数を提供します。
"""

import csv
from typing import Dict, List, Any, Optional, Tuple
import io
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta  # type: ignore
import pytz  # type: ignore
from sqlalchemy.orm import Session

from ..core.config import logger
from ..crud.user import user
from ..crud.attendance import attendance
from ..crud.location import location

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

def get_work_entries_csv(db: Session, month: Optional[str] = None, encoding: str = "utf-8") -> bytes:
    """
    勤怠データをCSV形式で取得します

    Args:
        db: データベースセッション
        month: 'YYYY-MM'形式の月文字列（Noneの場合は全期間）
        encoding: CSVのエンコーディング（'utf-8'または'sjis'）

    Returns:
        bytes: エンコードされたCSVデータ
    """
    # CSVバッファを初期化
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # 日付列のヘッダー（年月日）を作成
    today = datetime.now().date()
    
    # 月が指定されている場合、その月の日付に限定
    if month:
        start_date, end_date = get_date_range_for_month(month)
        current_date = start_date
        date_headers = []
        
        # 指定月の全日付をヘッダーに追加
        while current_date <= end_date:
            date_headers.append(current_date.strftime("%Y/%m/%d"))
            current_date = current_date + relativedelta(days=1)
    else:
        # 月指定がない場合、3ヶ月分のデータを表示
        date_headers = []
        for i in range(90):  # 90日分
            d = today - relativedelta(days=i)
            date_headers.append(d.strftime("%Y/%m/%d"))
        
        # 日付順に並べ替え
        date_headers.sort()
    
    # ヘッダー行を書き込み
    headers = ["user_name", "user_id", "group_name", "is_contractor"] + date_headers
    csv_writer.writerow(headers)
    
    # ユーザーデータを取得
    users_data = user.get_all_users(db)
    
    # 各ユーザーについて行を作成
    for user_name, user_id, is_contractor in users_data:
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            continue
            
        # ユーザーの所属グループを取得
        group_name = user_obj.group.name if user_obj.group else ""
        
        # ユーザーの勤怠データを取得
        user_entries = attendance.get_user_data(db, user_id=user_id)
        
        # 勤怠データを日付ごとのマップに変換
        user_locations = {}
        for entry in user_entries:
            date_key = entry["date"]
            location_name = entry["location_name"]
            user_locations[date_key] = location_name
        
        # 行データ作成
        row_data = [user_name, user_id, group_name, "true" if is_contractor else "false"]
        
        # 各日付列のデータを追加
        for date_str in date_headers:
            # YYYY/MM/DD形式からYYYY-MM-DD形式に変換
            date_parts = date_str.split("/")
            db_date_str = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
            
            # 該当日の勤務場所を取得
            location_name = user_locations.get(db_date_str, "")
            row_data.append(location_name)
        
        # CSVに行を書き込み
        csv_writer.writerow(row_data)
    
    # CSVデータを文字列として取得
    csv_content = output.getvalue()
    output.close()
    
    # 指定されたエンコーディングに変換
    if encoding.lower() == "sjis":
        return csv_content.encode("shift_jis", errors="replace")
    else:
        return csv_content.encode("utf-8") 