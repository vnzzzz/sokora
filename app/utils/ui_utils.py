"""
UI表示ユーティリティ
----------------

UI表示関連のユーティリティ関数を提供します。
主にTailwindCSSのスタイル生成とUIデータ操作に関する関数が含まれています。
"""

from typing import List, Dict, Any, Optional, TypedDict, Union, Callable, TypeVar, Generic, cast


# 型定義
class LocationBase(TypedDict):
    """勤務場所の基本情報型定義"""
    name: str
    badge: str


class LocationData(LocationBase):
    """勤務場所の詳細情報型定義"""
    color: str
    key: str


# Tailwind CSSで使用する色のリスト
TAILWIND_COLORS = [
    "success", "primary", "warning", "error", 
    "info", "accent", "secondary"
]


def _get_color_for_index(index: int) -> str:
    """インデックスに応じた色を取得します。

    Args:
        index: 色のインデックス

    Returns:
        str: 色名
    """
    return TAILWIND_COLORS[index % len(TAILWIND_COLORS)]


# 型変数の定義
T = TypeVar('T', LocationBase, LocationData)


def _map_locations(
    location_types: List[str], 
    transform_fn: Callable[[str, str], T]
) -> List[T]:
    """勤務場所リストを変換して新しいフォーマットに変換します。

    Args:
        location_types: 勤務場所タイプのリスト
        transform_fn: 変換関数（勤務場所名と色を受け取り、変換済みのデータを返す）

    Returns:
        List[T]: 変換された勤務場所リスト
    """
    return [
        transform_fn(loc_type, _get_color_for_index(i))
        for i, loc_type in enumerate(location_types)
    ]


def generate_location_styles(location_types: List[str]) -> Dict[str, str]:
    """勤務場所のスタイル情報を生成します。

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        Dict[str, str]: 勤務場所とそのスタイル情報のマッピング
    """
    return {
        loc_type: f"text-{_get_color_for_index(i)}"
        for i, loc_type in enumerate(location_types)
    }


def generate_location_badges(location_types: List[str]) -> List[LocationBase]:
    """勤務場所のバッジ情報を生成します。

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        List[LocationBase]: 勤務場所とそのバッジ情報のリスト
    """
    def transform(loc: str, color: str) -> LocationBase:
        return {"name": loc, "badge": color}
        
    return _map_locations(location_types, transform)


def generate_location_data(location_types: List[str]) -> List[LocationData]:
    """勤務場所の詳細なスタイル情報を生成します。

    generate_location_badgesより詳細な情報を含む拡張バージョンです。

    Args:
        location_types: 勤務場所タイプのリスト

    Returns:
        List[LocationData]: 勤務場所とそのスタイル情報のリスト
    """
    def transform(loc: str, color: str) -> LocationData:
        return {
            "name": loc,
            "color": f"text-{color}",
            "key": loc,
            "badge": color,
        }
        
    return _map_locations(location_types, transform)


def has_data_for_day(day_data: Dict[str, List]) -> bool:
    """特定の日にデータが存在するかどうかをチェックします。

    Args:
        day_data: 日別データ（勤務場所をキー、ユーザーリストを値とする辞書）

    Returns:
        bool: データが存在する場合はTrue、そうでない場合はFalse
    """
    # 辞書が空でなく、少なくとも1つのキーに値が存在する場合はTrueを返す
    return bool(day_data) and any(bool(users) for users in day_data.values())
