"""UI表示用のsemantic presentation tokenを提供する。

Tailwind / daisyUI class名はserver-sideで生成しない。動的な見た目はsemantic tokenとして
templateへ渡し、actual stylingはbuilder/input.cssだけが所有する。
"""

from typing import Dict, List, Optional, TypedDict

LOCATION_TONE_COUNT = 7
DEFAULT_LOCATION_TONE = 0
UNRESOLVED_LOCATION_TONE = -1


class LocationData(TypedDict):
    """calendar templateへ渡す勤怠種別presentation contract。"""

    name: str
    key: str
    tone: int


def get_location_tone(location_id: Optional[int]) -> int:
    """Location IDをstableなpalette slotへ変換する。"""
    if location_id is None:
        return DEFAULT_LOCATION_TONE
    return location_id % LOCATION_TONE_COUNT


def generate_location_data(location_types: List[str]) -> List[LocationData]:
    """勤怠種別名からcalendar用のsemantic location dataを作る。"""
    return [
        {
            "name": location_name,
            "key": location_name,
            "tone": get_location_tone(index),
        }
        for index, location_name in enumerate(location_types)
    ]


def has_data_for_day(day_data: Dict[str, List]) -> bool:
    """特定の日に1件以上のデータが存在するかを返す。"""
    return bool(day_data) and any(bool(users) for users in day_data.values())
