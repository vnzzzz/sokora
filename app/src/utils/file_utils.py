"""
ファイル操作ユーティリティ
-----------------

ファイル操作に関連するユーティリティ関数
"""

import os
from pathlib import Path
import csv
from typing import Dict, List, Optional, Tuple
import logging
from ..utils.date_utils import normalize_date_format, parse_date

# ロガー設定
logger = logging.getLogger(__name__)


def get_csv_file_path() -> Path:
    """CSVファイルの場所を特定する関数

    Returns:
        Path: CSVファイルへのパス
    """
    possible_paths = [
        "work_entries.csv",  # 基本パス
        os.path.join(os.getcwd(), "work_entries.csv"),  # 現在のディレクトリ
        os.path.join(os.getcwd(), "data", "work_entries.csv"),  # data/ディレクトリ
        os.path.join(
            os.path.dirname(os.getcwd()), "data", "work_entries.csv"
        ),  # 親ディレクトリのdata/
        os.path.join(os.getcwd(), "app", "work_entries.csv"),  # Docker環境用
        os.path.join(
            os.getcwd(), "app", "data", "work_entries.csv"
        ),  # Docker環境用のdata/
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return Path(path)

    # 見つからない場合は基本パスを返す（新しいファイル作成用）
    return Path("work_entries.csv")


def import_csv_data(content: str) -> None:
    """CSVデータをファイルに保存します

    Args:
        content: CSVファイルの内容

    Raises:
        IOError: ファイル書き込みに失敗した場合
    """
    try:
        # CSV内容を解析
        reader = csv.reader(content.splitlines())
        rows = list(reader)

        if not rows:
            raise IOError("CSV内容が空です")

        # ヘッダー取得
        headers = rows[0]

        # ヘッダーの日付形式を正規化
        if len(headers) > 2:  # 日付列があることを確認
            for i in range(2, len(headers)):
                if parse_date(headers[i]):
                    # 日付の場合、YYYY-MM-DD形式に正規化
                    headers[i] = normalize_date_format(headers[i])

        # 正規化されたヘッダーで新しいCSV内容を作成
        output = []
        output.append(",".join(headers))
        for row in rows[1:]:
            output.append(",".join(row))

        normalized_content = "\n".join(output)

        # ファイルに書き込み
        with get_csv_file_path().open("w", encoding="utf-8-sig", newline="") as f:
            f.write(normalized_content)
    except Exception as e:
        logger.error(f"CSVデータの書き込みに失敗しました: {str(e)}")
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")


def read_csv_file() -> Tuple[List[str], List[List[str]]]:
    """CSVファイルからヘッダーと行データを読み込みます

    Returns:
        Tuple[List[str], List[List[str]]]: (ヘッダーのリスト, 行データのリスト)

    Raises:
        IOError: ファイル読み込みに失敗した場合
    """
    csv_path = get_csv_file_path()
    headers = []
    rows = []

    if not csv_path.exists():
        return headers, rows

    try:
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(
                reader, []
            )  # ヘッダー行を読み込み、ファイルが空の場合は空リストを返す
            rows = list(reader)
    except Exception as e:
        logger.error(f"CSVデータの読み込みに失敗しました: {str(e)}")
        raise IOError(f"CSVデータの読み込みに失敗しました: {str(e)}")

    return headers, rows


def write_csv_file(headers: List[str], rows: List[List[str]]) -> None:
    """ヘッダーと行データをCSVファイルに書き込みます

    Args:
        headers: ヘッダー行のリスト
        rows: データ行のリスト

    Raises:
        IOError: ファイル書き込みに失敗した場合
    """
    csv_path = get_csv_file_path()

    try:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"CSVデータの書き込みに失敗しました: {str(e)}")
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")
