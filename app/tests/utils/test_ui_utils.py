"""UI semantic presentation token tests."""

from app.utils.ui_utils import get_location_tone


def test_location_tone_cycles_after_thirty_slots() -> None:
    assert get_location_tone(1) == 1
    assert get_location_tone(29) == 29
    assert get_location_tone(30) == 0
    assert get_location_tone(31) == 1
