"""
UI表示ユーティリティ
----------------

UI表示関連のユーティリティ関数
"""

from typing import List, Dict, Any


def generate_location_styles(location_types: List[str]) -> Dict[str, str]:
    """勤務場所のスタイル情報を生成します

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        Dict[str, str]: 勤務場所とそのスタイル情報のマッピング
    """
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    location_styles = {}

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        location_styles[loc_type] = (
            f"bg-{colors[color_index]}/10 text-{colors[color_index]}"
        )

    return location_styles


def generate_location_badges(location_types: List[str]) -> List[Dict[str, str]]:
    """勤務場所のバッジ情報を生成します

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        List[Dict[str, str]]: 勤務場所とそのバッジ情報のリスト
    """
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


def generate_location_data(location_types: List[str]) -> List[Dict[str, str]]:
    """勤務場所のスタイル情報を生成します

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        List[Dict[str, str]]: 勤務場所とそのスタイル情報のリスト
    """
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

    return locations


def has_data_for_day(day_data: Dict[str, List]) -> bool:
    """特定の日にデータが存在するかどうかをチェックします

    Args:
        day_data: 日別データ（勤務場所をキー、ユーザーリストを値とする辞書）

    Returns:
        bool: データが存在する場合はTrue、そうでない場合はFalse
    """
    return bool(day_data)
