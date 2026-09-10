"""UI表示用のsemantic presentation tokenを提供する。

Tailwind / daisyUI class名はserver-sideで生成しない。動的な見た目はsemantic tokenとして
templateへ渡し、actual stylingはbuilder/input.cssだけが所有する。
"""

LOCATION_TONE_COUNT = 10
UNRESOLVED_LOCATION_TONE = -1


def get_location_tone(location_id: int) -> int:
    """Location IDをstableな10個のpalette slotへ変換する。"""
    return location_id % LOCATION_TONE_COUNT
