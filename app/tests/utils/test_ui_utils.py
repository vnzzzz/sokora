"""UI semantic presentation token tests."""

from app.utils.ui_utils import get_location_tone


def test_location_tone_cycles_after_ten_slots() -> None:
    assert get_location_tone(1) == 1
    assert get_location_tone(9) == 9
    assert get_location_tone(10) == 0
    assert get_location_tone(11) == 1
