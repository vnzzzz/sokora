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

# ロガー設定
logger = logging.getLogger(__name__)


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
        logger.error(f"CSVデータの書き込みに失敗しました: {str(e)}")
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")


def read_csv_file() -> Tuple[List[str], List[List[str]]]:
    """CSVファイルからヘッダーと行データを読み込む

    Returns:
        Tuple[List[str], List[List[str]]]: (ヘッダーのリスト, 行データのリスト)

    Raises:
        IOError: ファイルの読み込みに失敗した場合
    """
    csv_path = get_csv_file_path()
    headers = []
    rows = []

    if not csv_path.exists():
        return headers, rows

    try:
        with csv_path.open("r", encoding="utf-8") as f:
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
    """ヘッダーと行データをCSVファイルに書き込む

    Args:
        headers: ヘッダー行のリスト
        rows: データ行のリスト

    Raises:
        IOError: ファイルの書き込みに失敗した場合
    """
    csv_path = get_csv_file_path()

    try:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"CSVデータの書き込みに失敗しました: {str(e)}")
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")
