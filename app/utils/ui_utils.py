"""
UI表示ユーティリティ
----------------

UI表示関連のユーティリティ関数を提供します。
主にTailwindCSSのスタイル生成とUIデータ操作に関する関数が含まれています。
"""

from typing import List, Dict, Optional, TypedDict, Callable, TypeVar


# 型定義
class LocationBase(TypedDict):
    """勤怠種別の基本情報型定義"""
    name: str
    badge: str


class LocationData(LocationBase):
    """勤怠種別の詳細情報型定義"""
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
        str: 色名 (例: "success", "primary")
    """
    # 常に正のインデックスを保証するために剰余演算子の前にリスト長を加算
    # (location ID が 0 以下の場合も考慮)
    positive_index = (index % len(TAILWIND_COLORS)) + len(TAILWIND_COLORS)
    return TAILWIND_COLORS[positive_index % len(TAILWIND_COLORS)]


def get_location_color_classes(location_id: Optional[int]) -> Dict[str, str]:
    """Location IDに基づいて文字色と背景色のCSSクラスを決定します。

    Args:
        location_id: 勤怠種別のID。Noneの場合はデフォルトの色を返します。

    Returns:
        Dict[str, str]: "text_class" と "bg_class" をキーに持つ辞書。
                         例: {"text_class": "text-success", "bg_class": "bg-success/15"}
    """
    if location_id is None:
        # IDがない場合 (例: 未分類など) はデフォルトの色 (例: neutralやbase) を返すか、
        # またはエラーを示す色にするか、仕様に応じて決定します。
        # ここではシンプルに最初の色を使いますが、必要に応じて変更してください。
        color_name = _get_color_for_index(0) 
    else:
        color_name = _get_color_for_index(location_id)

    return {
        "text_class": f"text-{color_name}",
        "bg_class": f"bg-{color_name}/15",  # DaisyUI v4 opacity format
    }


# 型変数の定義
T = TypeVar('T', LocationBase, LocationData)


def _map_locations(
    location_types: List[str], 
    transform_fn: Callable[[str, str], T]
) -> List[T]:
    """勤怠種別リストを変換して新しいフォーマットに変換します。

    Args:
        location_types: 勤怠種別タイプのリスト
        transform_fn: 変換関数（勤怠種別名と色を受け取り、変換済みのデータを返す）

    Returns:
        List[T]: 変換された勤怠種別リスト
    """
    return [
        transform_fn(loc_type, _get_color_for_index(i))
        for i, loc_type in enumerate(location_types)
    ]


def generate_location_styles(location_types: List[str]) -> Dict[str, str]:
    """勤怠種別のスタイル情報を生成します。

    Args:
        location_types: 勤怠種別タイプのリスト

    Returns:
        Dict[str, str]: 勤怠種別とそのスタイル情報のマッピング
    """
    return {
        loc_type: f"text-{_get_color_for_index(i)}"
        for i, loc_type in enumerate(location_types)
    }


def generate_location_badges(location_types: List[str]) -> List[LocationBase]:
    """勤怠種別のバッジ情報を生成します。

    Args:
        location_types: 勤怠種別タイプのリスト

    Returns:
        List[LocationBase]: 勤怠種別とそのバッジ情報のリスト
    """
    def transform(loc: str, color: str) -> LocationBase:
        return {"name": loc, "badge": color}
        
    return _map_locations(location_types, transform)


def generate_location_data(location_types: List[str]) -> List[LocationData]:
    """勤怠種別の詳細なスタイル情報を生成します。

    generate_location_badgesより詳細な情報を含む拡張バージョンです。

    Args:
        location_types: 勤怠種別タイプのリスト

    Returns:
        List[LocationData]: 勤怠種別とそのスタイル情報のリスト
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
        day_data: 日別データ（勤怠種別をキー、ユーザーリストを値とする辞書）

    Returns:
        bool: データが存在する場合はTrue、そうでない場合はFalse
    """
    # 辞書が空でなく、少なくとも1つのキーに値が存在する場合はTrueを返す
    return bool(day_data) and any(bool(users) for users in day_data.values())
