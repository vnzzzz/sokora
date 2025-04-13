import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime
import os
import logging
from typing import Dict, List, Optional, Any, DefaultDict, Tuple, Set

from ..utils.file_utils import get_csv_file_path, read_csv_file, write_csv_file
from ..utils.calendar_utils import (
    parse_month,
    get_prev_month_date,
    get_next_month_date,
    generate_location_data,
    create_calendar_weeks,
)
from ..utils.common import get_default_location_types

# ロガー設定
logger = logging.getLogger(__name__)

# 日本のカレンダー設定（0:月曜始まり → 6:日曜始まり）
calendar.setfirstweekday(6)


def get_location_types() -> List[str]:
    """CSVから勤務場所の種類を動的に取得する関数

    Returns:
        List[str]: 勤務場所の種類のリスト
    """
    data = read_all_entries()
    locations: Set[str] = set()

    # すべてのユーザーデータから勤務場所を抽出
    for user_data in data.values():
        for location in user_data.values():
            if location.strip():  # 空白でない場合
                locations.add(location)

    # デフォルトの勤務場所タイプがない場合の対応
    if not locations:
        return get_default_location_types()

    return sorted(list(locations))


def import_csv_data(content: str) -> None:
    """CSVデータをファイルに保存する

    Args:
        content: CSVファイルの内容

    Raises:
        IOError: ファイルの書き込みに失敗した場合
    """
    from ..utils.file_utils import import_csv_data as file_import_csv_data

    try:
        file_import_csv_data(content)
    except IOError as e:
        logger.error(f"CSVデータのインポートに失敗しました: {str(e)}")
        raise


def read_all_entries() -> Dict[str, Dict[str, str]]:
    """CSVファイルからすべてのエントリーを読み込む

    Returns:
        Dict[str, Dict[str, str]]: {user_id: {date: location}}形式のデータ
    """
    headers, rows = read_csv_file()
    data: Dict[str, Dict[str, str]] = {}

    if not headers:
        return data

    dates = headers[2:]  # 最初の列はuser_name、2列目はuser_id

    for row in rows:
        if len(row) < 2:  # user_nameとuser_idが最低限必要
            continue

        user_id = row[1]
        user_data: Dict[str, str] = {}

        for i, location in enumerate(row[2:], 2):
            if (
                i < len(headers) and location.strip()
            ):  # 空欄でない場合かつインデックスが有効な場合のみ登録
                date = headers[i]
                user_data[date] = location

        data[user_id] = user_data

    return data


def get_entries_by_date() -> DefaultDict[str, Dict[str, str]]:
    """日付ごとのエントリーを取得する

    Returns:
        DefaultDict[str, Dict[str, str]]: {date: {user_id: location}}形式のデータ
    """
    data = read_all_entries()
    date_entries: DefaultDict[str, Dict[str, str]] = defaultdict(dict)

    # ユーザーごとのデータを日付ごとのデータに変換
    for user_id, user_data in data.items():
        for date, location in user_data.items():
            date_entries[date][user_id] = location

    return date_entries


def get_all_users() -> List[Tuple[str, str]]:
    """CSVファイルからすべてのユーザー名とIDを取得する

    Returns:
        List[Tuple[str, str]]: (user_name, user_id)のリスト
    """
    headers, rows = read_csv_file()
    users = []

    for row in rows:
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            users.append((row[0], row[1]))  # (user_name, user_id)のタプル

    return sorted(users, key=lambda x: x[0])  # user_nameでソート


def get_user_name_by_id(user_id: str) -> str:
    """ユーザーIDからユーザー名を取得する

    Args:
        user_id: ユーザーID

    Returns:
        str: ユーザー名（見つからない場合は空文字）
    """
    headers, rows = read_csv_file()

    for row in rows:
        if len(row) >= 2 and row[1] == user_id:
            return row[0]

    return ""


def add_user(username: str, user_id: str) -> bool:
    """CSVファイルに新しいユーザーを追加する

    Args:
        username: 追加するユーザー名
        user_id: ユーザーID

    Returns:
        bool: 追加が成功したかどうか
    """
    if not username.strip() or not user_id.strip():
        return False

    try:
        # 現在のデータを読み込む
        users = get_all_users()

        # ユーザー名またはIDにすでに同じものが存在する場合は追加しない
        for name, id in users:
            if name == username or id == user_id:
                return False

        # ファイルを読み込み、ヘッダーを取得
        headers, rows = read_csv_file()

        if not headers:
            # ファイルが存在しない場合は新規作成
            headers = ["user_name", "user_id"]

        # 新しいユーザーを追加
        new_row = [username, user_id] + [""] * (len(headers) - 2)
        rows.append(new_row)

        # ファイルに書き込む
        write_csv_file(headers, rows)

        return True
    except Exception as e:
        logger.error(f"ユーザーの追加に失敗しました: {str(e)}")
        raise IOError(f"ユーザーの追加に失敗しました: {str(e)}")


def delete_user(user_id: str) -> bool:
    """CSVファイルからユーザーを削除する

    Args:
        user_id: 削除するユーザーID

    Returns:
        bool: 削除が成功したかどうか
    """
    try:
        # ファイルを読み込む
        headers, rows = read_csv_file()

        if not headers:
            return False

        original_row_count = len(rows)
        # user_idに一致しない行だけを残す
        filtered_rows = [row for row in rows if len(row) < 2 or row[1] != user_id]

        # 行が削除されなかった場合（該当するユーザーがいない場合）
        if len(filtered_rows) == original_row_count:
            return False

        # ファイルに書き込む
        write_csv_file(headers, filtered_rows)

        return True
    except Exception as e:
        logger.error(f"ユーザーの削除に失敗しました: {str(e)}")
        raise IOError(f"ユーザーの削除に失敗しました: {str(e)}")


def update_user_entry(user_id: str, date: str, location: str) -> bool:
    """ユーザーの特定の日付の勤務場所を更新する

    Args:
        user_id: ユーザーID
        date: YYYY-MM-DD形式の日付
        location: 勤務場所

    Returns:
        bool: 更新が成功したかどうか
    """
    try:
        # ファイルを読み込む
        headers, rows = read_csv_file()

        if not headers:
            return False

        # 日付が存在するかチェック
        if date not in headers[2:]:
            # 日付が存在しない場合は適切な位置に挿入する
            date_headers = headers[2:]

            # 適切な挿入位置を探す
            insert_position = 2  # デフォルトは最初の日付位置

            # 日付が既存の日付より未来の場合、適切な位置を探す
            for i, existing_date in enumerate(date_headers):
                if existing_date > date:
                    # 挿入位置を見つけた
                    insert_position = i + 2  # headers[0]とheaders[1]の分を加算
                    break
                else:
                    # 最後まで到達した場合、末尾に追加
                    insert_position = len(headers)

            # 新しい日付をヘッダーに挿入
            headers.insert(insert_position, date)

            # すべての行に新しい列を挿入
            for row in rows:
                # 行が短い場合は必要な長さまで拡張
                while len(row) < insert_position:
                    row.append("")
                row.insert(insert_position, "")

        # 日付のインデックスを取得
        date_index = headers.index(date)

        # ユーザーが存在するかチェック
        user_exists = False
        for row in rows:
            if len(row) >= 2 and row[1] == user_id:
                user_exists = True
                # 行が短い場合は拡張
                while len(row) <= date_index:
                    row.append("")
                row[date_index] = location
                break

        # ユーザーが存在しない場合は何もしない
        if not user_exists:
            return False

        # ファイルに書き込む
        write_csv_file(headers, rows)

        return True
    except Exception as e:
        logger.error(f"エントリーの更新に失敗しました: {str(e)}")
        raise IOError(f"エントリーの更新に失敗しました: {str(e)}")


def get_calendar_data(month: str) -> Dict[str, Any]:
    """月ごとのカレンダーデータを生成する

    Args:
        month: YYYY-MM形式の月指定

    Returns:
        Dict: カレンダー表示に必要なデータ

    Raises:
        ValueError: 無効な月フォーマットの場合
    """
    date_entries = get_entries_by_date()
    location_types = get_location_types()
    calendar_dict: DefaultDict[int, Dict[str, int]] = defaultdict(
        lambda: {location_type: 0 for location_type in location_types}
    )

    # 月データの解析
    year, month_num = parse_month(month)

    # カレンダー用のデータ
    cal = calendar.monthcalendar(year, month_num)

    # エントリーデータの集計
    for date, entries in date_entries.items():
        if date.startswith(month):
            try:
                day = int(date.split("-")[2])
                for _, location in entries.items():
                    if location in location_types:
                        calendar_dict[day][location] += 1
            except (IndexError, ValueError):
                continue  # 無効な日付形式はスキップ

    # 週ごとにまとめたカレンダーデータを作成
    calendar_weeks = create_calendar_weeks(cal, month, calendar_dict, location_types)

    # 勤務場所のスタイル情報を生成
    locations = generate_location_data(location_types)

    # 前月・翌月の計算
    prev_month_date = get_prev_month_date(year, month_num)
    next_month_date = get_next_month_date(year, month_num)

    # 日本語の月名取得
    month_name = f"{year}年{month_num}月"

    return {
        "weeks": calendar_weeks,
        "prev_month": f"{prev_month_date.year}-{prev_month_date.month:02d}",
        "next_month": f"{next_month_date.year}-{next_month_date.month:02d}",
        "month_name": month_name,
        "locations": locations,
    }


def get_day_data(day: str) -> Dict[str, List[Dict[str, str]]]:
    """指定された日のデータを取得する

    Args:
        day: YYYY-MM-DD形式の日付

    Returns:
        Dict[str, List[Dict[str, str]]]: ロケーション別のユーザー一覧（user_nameとuser_idを含む）

    Raises:
        ValueError: 無効な日付フォーマットの場合
    """
    entries_by_date = get_entries_by_date()
    location_types = get_location_types()
    result: Dict[str, List[Dict[str, str]]] = {
        loc_type: [] for loc_type in location_types
    }

    # 日付の検証
    parts = day.split("-")
    if len(parts) != 3:
        return result

    # 特定の日の各ユーザーの勤務場所を集計
    for user_id, location in entries_by_date.get(day, {}).items():
        user_name = get_user_name_by_id(user_id)
        user_data = {"user_id": user_id, "user_name": user_name}

        # すべての勤務場所を受け入れる
        if location in result:
            result[location].append(user_data)
        # CSVにあるが辞書にないロケーションタイプの場合は追加する
        elif location.strip():
            result[location] = [user_data]

    return result


def get_user_data(user_id: str) -> List[Dict[str, str]]:
    """指定されたユーザーのデータを取得する

    Args:
        user_id: ユーザーID

    Returns:
        List[Dict[str, str]]: ユーザーのエントリー一覧
    """
    data = read_all_entries()
    entries = []

    if user_id in data:
        user_data = data[user_id]
        for date, location in user_data.items():
            entries.append({"date": date, "location": location})

    # 日付でソート
    entries.sort(key=lambda x: x["date"])
    return entries
