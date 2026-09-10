"""UI semantic presentation token tests."""

from app.utils.ui_utils import DEFAULT_LOCATION_TONE, get_location_tone


def test_location_tone_uses_ten_stable_palette_slots() -> None:
    assert get_location_tone(1) == 1
    assert get_location_tone(9) == 9
    assert get_location_tone(10) == 0
    assert get_location_tone(11) == 1


def test_location_tone_uses_default_for_missing_identity() -> None:
    assert get_location_tone(None) == DEFAULT_LOCATION_TONE
