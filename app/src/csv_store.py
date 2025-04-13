import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime
import os
from typing import Dict, List, Optional, Any, DefaultDict, Tuple, Set


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
        return ["在宅", "出社", "出張"]

    return sorted(list(locations))


def get_csv_file_path() -> Path:
    """CSV_FILEの場所を特定する関数

    Returns:
        Path: CSVファイルのパス
    """
    possible_paths = [
        "work_entries.csv",  # 基本パス
        os.path.join(os.getcwd(), "work_entries.csv"),  # カレントディレクトリ
        os.path.join(os.getcwd(), "data", "work_entries.csv"),  # data/ディレクトリ
        os.path.join(
            os.path.dirname(os.getcwd()), "data", "work_entries.csv"
        ),  # 親ディレクトリのdata/
        os.path.join(os.getcwd(), "app", "work_entries.csv"),  # Docker環境用
        os.path.join(
            os.getcwd(), "app", "data", "work_entries.csv"
        ),  # Docker環境用data/
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return Path(path)

    # 存在しない場合は基本パスを返す（新規作成用）
    return Path("work_entries.csv")


def import_csv_data(content: str) -> None:
    """CSVデータをファイルに保存する

    Args:
        content: CSVファイルの内容

    Raises:
        IOError: ファイルの書き込みに失敗した場合
    """
    try:
        with get_csv_file_path().open("w", encoding="utf-8", newline="") as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")


def read_all_entries() -> Dict[str, Dict[str, str]]:
    """CSVファイルからすべてのエントリーを読み込む

    Returns:
        Dict[str, Dict[str, str]]: {user_id: {date: location}}形式のデータ
    """
    csv_path = get_csv_file_path()
    if not csv_path.exists():
        return {}

    data: Dict[str, Dict[str, str]] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # 日付がヘッダーに格納されている
            dates = headers[2:]  # 最初の列はuser_name、2列目はuser_id

            for row in reader:
                if len(row) < 2:  # user_nameとuser_idが最低限必要
                    continue

                user_id = row[1]
                user_data: Dict[str, str] = {}

                for i, location in enumerate(row[2:], 2):
                    if location and i <= len(
                        headers
                    ):  # 空欄でない場合かつインデックスが有効な場合のみ登録
                        date = headers[i]
                        user_data[date] = location

                data[user_id] = user_data
    except Exception as e:
        raise IOError(f"CSVデータの読み込みに失敗しました: {str(e)}")

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
    csv_path = get_csv_file_path()
    if not csv_path.exists():
        return []

    users = []

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # ヘッダー行をスキップ

            for row in reader:
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    users.append((row[0], row[1]))  # (user_name, user_id)のタプル
    except Exception as e:
        raise IOError(f"ユーザーデータの読み込みに失敗しました: {str(e)}")

    return sorted(users, key=lambda x: x[0])  # user_nameでソート


def get_user_name_by_id(user_id: str) -> str:
    """ユーザーIDからユーザー名を取得する

    Args:
        user_id: ユーザーID

    Returns:
        str: ユーザー名（見つからない場合は空文字）
    """
    csv_path = get_csv_file_path()
    if not csv_path.exists():
        return ""

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダー行をスキップ

            for row in reader:
                if len(row) >= 2 and row[1] == user_id:
                    return row[0]
    except Exception:
        pass

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

    csv_path = get_csv_file_path()

    try:
        # 現在のデータを読み込む
        users = get_all_users()

        # ユーザー名またはIDにすでに同じものが存在する場合は追加しない
        for name, id in users:
            if name == username or id == user_id:
                return False

        # ファイルを読み込み、ヘッダーを取得
        headers = []
        rows = []

        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)
        else:
            # ファイルが存在しない場合は新規作成
            headers = ["user_name", "user_id"]

        # 新しいユーザーを追加
        new_row = [username, user_id] + [""] * (len(headers) - 2)
        rows.append(new_row)

        # ファイルに書き込む
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return True
    except Exception as e:
        raise IOError(f"ユーザーの追加に失敗しました: {str(e)}")


def delete_user(user_id: str) -> bool:
    """CSVファイルからユーザーを削除する

    Args:
        user_id: 削除するユーザーID

    Returns:
        bool: 削除が成功したかどうか
    """
    csv_path = get_csv_file_path()

    if not csv_path.exists():
        return False

    try:
        # ファイルを読み込む
        headers = []
        rows = []

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = [row for row in reader if len(row) < 2 or row[1] != user_id]

        # 行が削除されなかった場合（該当するユーザーがいない場合）
        original_count = sum(1 for _ in open(csv_path, encoding="utf-8")) - 1
        if len(rows) == original_count:
            return False

        # ファイルに書き込む
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return True
    except Exception as e:
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
    csv_path = get_csv_file_path()

    if not csv_path.exists():
        return False

    try:
        # ファイルを読み込む
        headers = []
        rows = []

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

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
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return True
    except Exception as e:
        raise IOError(f"エントリーの更新に失敗しました: {str(e)}")


def parse_month(month: str) -> Tuple[int, int]:
    """YYYY-MM形式の文字列を年と月に分解する

    Args:
        month: YYYY-MM形式の月指定

    Returns:
        Tuple[int, int]: (年, 月)のタプル

    Raises:
        ValueError: 無効な月フォーマットの場合
    """
    try:
        year, month_num = map(int, month.split("-"))
        if month_num < 1 or month_num > 12:
            raise ValueError(f"無効な月番号: {month_num}")
        return year, month_num
    except Exception:
        raise ValueError(
            f"無効な月フォーマット: {month}。YYYY-MM形式で指定してください。"
        )


def get_prev_month_date(year: int, month: int) -> datetime.date:
    """前月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 前月の日付オブジェクト
    """
    if month == 1:
        return datetime.date(year - 1, 12, 1)
    return datetime.date(year, month - 1, 1)


def get_next_month_date(year: int, month: int) -> datetime.date:
    """翌月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の日付オブジェクト
    """
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)


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
    calendar_weeks = []

    for week in cal:
        week_data = []
        for day in week:
            if day == 0:  # 0は月の範囲外の日
                week_data.append(None)
            else:
                day_data = {
                    "day": day,
                    "date": f"{month}-{day:02d}",
                }
                # 各勤務場所タイプのカウントをデータに追加
                for loc_type in location_types:
                    day_data[loc_type] = calendar_dict[day].get(loc_type, 0)
                week_data.append(day_data)
        calendar_weeks.append(week_data)

    # 勤務場所のスタイル情報を生成
    # 固定の色情報を使用
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []
    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "color": f"text-{colors[color_index]}",
                "key": loc_type,
                "badge": colors[color_index],
            }
        )

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
