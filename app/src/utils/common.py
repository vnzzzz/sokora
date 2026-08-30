"""
共通ユーティリティ関数
-----------------

複数のモジュールで使用する共通ユーティリティ関数
"""

from typing import List, Dict, Any
from .. import csv_store


def generate_location_styles() -> Dict[str, str]:
    """勤務場所のスタイル情報を生成する

    Returns:
        Dict[str, str]: 勤務場所とそのスタイル情報のマッピング
    """
    location_types = csv_store.get_location_types()
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    location_styles = {}

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        location_styles[loc_type] = (
            f"bg-{colors[color_index]}/10 text-{colors[color_index]}"
        )

    return location_styles


def generate_location_badges() -> List[Dict[str, str]]:
    """勤務場所のバッジ情報を生成する

    Returns:
        List[Dict[str, str]]: 勤務場所とそのバッジ情報のリスト
    """
    location_types = csv_store.get_location_types()
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "badge": colors[color_index],
            }
        )

    return locations


def has_data_for_day(day_data: Dict[str, List[str]]) -> bool:
    """日別データに勤務情報があるかどうかを確認する

    Args:
        day_data: 日別データ（勤務場所ごとのユーザーリスト）

    Returns:
        bool: データがあればTrue、なければFalse
    """
    return any(len(users) > 0 for users in day_data.values())
