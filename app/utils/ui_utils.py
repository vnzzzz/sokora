"""UI表示用のsemantic presentation tokenを提供する。

Tailwind / daisyUI class名はserver-sideで生成しない。動的な見た目はsemantic tokenとして
templateへ渡し、actual stylingはbuilder/input.cssだけが所有する。
"""

LOCATION_TONE_COUNT = 30
UNRESOLVED_LOCATION_TONE = -1


def get_location_tone(location_id: int) -> int:
    """Location IDをstableな30個のpalette slotへ変換する。

    Args:
        location_id: 永続的なLocation primary key。

    Returns:
        `0..LOCATION_TONE_COUNT-1`のstable palette index。
    """
    return location_id % LOCATION_TONE_COUNT
