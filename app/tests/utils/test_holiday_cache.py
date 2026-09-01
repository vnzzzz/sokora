"""holiday_cache contract tests."""

import datetime
import json
from typing import Any
from unittest.mock import mock_open, patch

from app.utils.holiday_cache import (
    HolidayCache,
    bind_custom_holiday_snapshot,
    get_cache_info,
    get_holiday_name,
    is_holiday,
    reset_custom_holiday_snapshot,
)


class TestHolidayCache:
    @patch("app.utils.holiday_cache.CACHE_FILE")
    def test_init_with_existing_build_time_cache(self, mock_cache_file: Any) -> None:
        cache_data = {
            "holidays": {"2024-01-01": "元日", "2024-05-03": "憲法記念日"},
            "build_time": True,
        }
        mock_cache_file.exists.return_value = True

        with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            holiday_cache = HolidayCache()

        assert holiday_cache._cache == cache_data["holidays"]
        assert holiday_cache._build_time_cache is True

    @patch("app.utils.holiday_cache.CACHE_FILE")
    def test_init_with_existing_legacy_cache(self, mock_cache_file: Any) -> None:
        cache_data = {"holidays": {"2024-01-01": "元日"}}
        mock_cache_file.exists.return_value = True

        with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            holiday_cache = HolidayCache()

        assert holiday_cache._cache == cache_data["holidays"]
        assert holiday_cache._build_time_cache is False

    @patch("app.utils.holiday_cache.CACHE_FILE")
    def test_init_with_no_cache(self, mock_cache_file: Any) -> None:
        mock_cache_file.exists.return_value = False

        holiday_cache = HolidayCache()

        assert holiday_cache._cache == {}
        assert holiday_cache._build_time_cache is False

    @patch("app.utils.holiday_cache.CACHE_FILE")
    def test_init_with_invalid_cache(self, mock_cache_file: Any) -> None:
        mock_cache_file.exists.return_value = True

        with patch("builtins.open", mock_open(read_data="invalid json")):
            holiday_cache = HolidayCache()

        assert holiday_cache._cache == {}
        assert holiday_cache._build_time_cache is False

    def test_static_holiday_lookup(self) -> None:
        holiday_cache = HolidayCache()
        holiday_cache._cache = {"2024-01-01": "元日"}

        assert holiday_cache.is_holiday(datetime.date(2024, 1, 1)) is True
        assert holiday_cache.get_holiday_name(datetime.date(2024, 1, 1)) == "元日"
        assert holiday_cache.is_holiday(datetime.date(2024, 1, 2)) is False
        assert holiday_cache.get_holiday_name(datetime.date(2024, 1, 2)) == ""

    @patch("app.utils.holiday_cache.CACHE_FILE")
    def test_get_cache_info_is_static_asset_only(self, mock_cache_file: Any) -> None:
        mock_cache_file.exists.return_value = True
        holiday_cache = HolidayCache()
        holiday_cache._cache = {
            "2024-01-01": "元日",
            "2025-01-01": "元日",
        }
        holiday_cache._build_time_cache = True

        result = holiday_cache.get_cache_info()

        assert result == {
            "total_holidays": 2,
            "build_time_cache": True,
            "cache_file_exists": True,
            "years_covered": ["2024", "2025"],
            "custom_total": 0,
        }


class TestRequestLocalHolidaySnapshot:
    @patch("app.utils.holiday_cache._holiday_cache")
    def test_custom_snapshot_overrides_static_holiday(
        self, mock_holiday_cache: Any
    ) -> None:
        target = datetime.date(2024, 12, 31)
        mock_holiday_cache.get_holiday_name.return_value = "標準休"
        token = bind_custom_holiday_snapshot({"2024-12-31": "社内特別休"})
        try:
            assert is_holiday(target) is True
            assert get_holiday_name(target) == "社内特別休"
        finally:
            reset_custom_holiday_snapshot(token)

        assert get_holiday_name(target) == "標準休"

    @patch("app.utils.holiday_cache._holiday_cache")
    def test_snapshot_does_not_leak_after_reset(self, mock_holiday_cache: Any) -> None:
        target = datetime.date(2031, 5, 13)
        mock_holiday_cache.get_holiday_name.return_value = ""

        token = bind_custom_holiday_snapshot({"2031-05-13": "Replica Holiday"})
        try:
            assert get_holiday_name(target) == "Replica Holiday"
        finally:
            reset_custom_holiday_snapshot(token)

        assert get_holiday_name(target) == ""


class TestGlobalFunctions:
    @patch("app.utils.holiday_cache._holiday_cache")
    def test_static_global_lookup_without_request_snapshot(
        self, mock_holiday_cache: Any
    ) -> None:
        mock_holiday_cache.get_holiday_name.return_value = "元日"
        target = datetime.date(2024, 1, 1)

        assert get_holiday_name(target) == "元日"
        assert is_holiday(target) is True

    @patch("app.utils.holiday_cache._holiday_cache")
    def test_get_cache_info_function(self, mock_holiday_cache: Any) -> None:
        expected_info = {
            "total_holidays": 10,
            "build_time_cache": True,
            "cache_file_exists": True,
            "years_covered": ["2024", "2025"],
            "custom_total": 0,
        }
        mock_holiday_cache.get_cache_info.return_value = expected_info

        assert get_cache_info() == expected_info
