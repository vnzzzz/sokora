"""
calendar_utils のテストケース
"""

import pytest
import datetime
from unittest.mock import MagicMock, patch
from fastapi import Request
from typing import List, Any

from app.utils.calendar_utils import (
    format_date, format_date_jp, get_today_formatted, get_current_month_formatted,
    get_last_viewed_date, parse_date, normalize_date_format, parse_month,
    get_prev_month_date, get_next_month_date, get_current_week_formatted,
    parse_week, get_prev_week_date, get_next_week_date, format_week_name,
    build_week_calendar_data, build_calendar_data, DateFormat, _detect_date_format,
    _split_date_string
)
from app.models.attendance import Attendance
from app.models.location import Location
from app.models.user import User


class TestDateFormats:
    """日付フォーマット関連のテスト"""

    def test_format_date(self) -> None:
        """format_date関数のテスト"""
        test_date = datetime.date(2024, 1, 15)
        result = format_date(test_date)
        assert result == "2024-01-15"

    def test_format_date_jp_with_date(self) -> None:
        """format_date_jp関数のテスト（日付あり）"""
        test_date = datetime.date(2024, 1, 15)  # 月曜日
        result = format_date_jp(test_date)
        assert result == "2024年1月15日(月)"

    def test_format_date_jp_with_none(self) -> None:
        """format_date_jp関数のテスト（None）"""
        result = format_date_jp(None)
        assert result == ""

    def test_format_date_jp_different_weekdays(self) -> None:
        """format_date_jp関数の曜日テスト"""
        # 2024-01-14は日曜日
        sunday = datetime.date(2024, 1, 14)
        assert format_date_jp(sunday) == "2024年1月14日(日)"
        
        # 2024-01-20は土曜日
        saturday = datetime.date(2024, 1, 20)
        assert format_date_jp(saturday) == "2024年1月20日(土)"

    @patch('app.utils.calendar_utils.datetime')
    def test_get_today_formatted(self, mock_datetime: Any) -> None:
        """get_today_formatted関数のテスト"""
        mock_datetime.date.today.return_value = datetime.date(2024, 1, 15)
        result = get_today_formatted()
        assert result == "2024-01-15"

    @patch('app.utils.calendar_utils.datetime')
    def test_get_current_month_formatted(self, mock_datetime: Any) -> None:
        """get_current_month_formatted関数のテスト"""
        mock_datetime.date.today.return_value = datetime.date(2024, 1, 15)
        result = get_current_month_formatted()
        assert result == "2024-01"


class TestDateDetection:
    """日付検出関連のテスト"""

    def test_detect_date_format_dash(self) -> None:
        """_detect_date_format関数のテスト（ダッシュ形式）"""
        result = _detect_date_format("2024-01-15")
        assert result == DateFormat.DASH

    def test_detect_date_format_slash(self) -> None:
        """_detect_date_format関数のテスト（スラッシュ形式）"""
        result = _detect_date_format("2024/01/15")
        assert result == DateFormat.SLASH

    def test_detect_date_format_invalid(self) -> None:
        """_detect_date_format関数のテスト（無効な形式）"""
        result = _detect_date_format("20240115")
        assert result is None

    def test_split_date_string_dash(self) -> None:
        """_split_date_string関数のテスト（ダッシュ形式）"""
        year, month, day = _split_date_string("2024-01-15")
        assert year == 2024
        assert month == 1
        assert day == 15

    def test_split_date_string_slash(self) -> None:
        """_split_date_string関数のテスト（スラッシュ形式）"""
        year, month, day = _split_date_string("2024/01/15")
        assert year == 2024
        assert month == 1
        assert day == 15

    def test_split_date_string_invalid(self) -> None:
        """_split_date_string関数のテスト（無効な形式）"""
        year, month, day = _split_date_string("invalid")
        assert year is None
        assert month is None
        assert day is None

    def test_split_date_string_non_numeric(self) -> None:
        """_split_date_string関数のテスト（非数値）"""
        year, month, day = _split_date_string("year-month-day")
        assert year is None
        assert month is None
        assert day is None


class TestDateParsing:
    """日付解析関連のテスト"""

    def test_parse_date_dash_format(self) -> None:
        """parse_date関数のテスト（ダッシュ形式）"""
        result = parse_date("2024-01-15")
        assert result == datetime.date(2024, 1, 15)

    def test_parse_date_slash_format(self) -> None:
        """parse_date関数のテスト（スラッシュ形式）"""
        result = parse_date("2024/01/15")
        assert result == datetime.date(2024, 1, 15)

    def test_parse_date_single_digit(self) -> None:
        """parse_date関数のテスト（一桁の月日）"""
        result = parse_date("2024-1-5")
        assert result == datetime.date(2024, 1, 5)

    def test_parse_date_invalid_format(self) -> None:
        """parse_date関数のテスト（無効な形式）"""
        result = parse_date("invalid-date")
        assert result is None

    def test_parse_date_invalid_date(self) -> None:
        """parse_date関数のテスト（無効な日付）"""
        result = parse_date("2024-13-32")
        assert result is None

    def test_normalize_date_format_valid(self) -> None:
        """normalize_date_format関数のテスト（有効な日付）"""
        result = normalize_date_format("2024/1/5")
        assert result == "2024-01-05"

    def test_normalize_date_format_invalid(self) -> None:
        """normalize_date_format関数のテスト（無効な日付）"""
        result = normalize_date_format("invalid-date")
        assert result == "invalid-date"

    def test_parse_month_dash_format(self) -> None:
        """parse_month関数のテスト（ダッシュ形式）"""
        year, month = parse_month("2024-01")
        assert year == 2024
        assert month == 1

    def test_parse_month_slash_format(self) -> None:
        """parse_month関数のテスト（スラッシュ形式）"""
        year, month = parse_month("2024/01")
        assert year == 2024
        assert month == 1

    def test_parse_month_invalid_format(self) -> None:
        """parse_month関数のテスト（無効な形式）"""
        with pytest.raises(ValueError):
            parse_month("invalid-month")


class TestLastViewedDate:
    """最後の表示日付関連のテスト"""

    def test_get_last_viewed_date_with_calendar_day(self) -> None:
        """get_last_viewed_date関数のテスト（カレンダー日付あり）"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "http://localhost:8000/calendar/day/2024-01-15?param=value"
        
        result = get_last_viewed_date(mock_request)
        assert result == "2024-01-15"

    def test_get_last_viewed_date_with_legacy_ui_day(self) -> None:
        """旧UIパスは無視して今日の日付を返すことを確認"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "http://localhost:8000/ui/calendar/day/2024-01-15?param=value"

        with patch('app.utils.calendar_utils.get_today_formatted') as mock_today:
            mock_today.return_value = "2024-02-01"
            result = get_last_viewed_date(mock_request)
            assert result == "2024-02-01"

    def test_get_last_viewed_date_with_legacy_api_day(self) -> None:
        """旧APIパスは無視して今日の日付を返すことを確認"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "http://localhost:8000/api/day/2024-01-15?param=value"

        with patch('app.utils.calendar_utils.get_today_formatted') as mock_today:
            mock_today.return_value = "2024-02-10"
            result = get_last_viewed_date(mock_request)
            assert result == "2024-02-10"

    def test_get_last_viewed_date_with_invalid_date(self) -> None:
        """get_last_viewed_date関数のテスト（無効な日付）"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "http://localhost:8000/calendar/day/invalid-date"
        
        with patch('app.utils.calendar_utils.get_today_formatted') as mock_today:
            mock_today.return_value = "2024-01-15"
            result = get_last_viewed_date(mock_request)
            assert result == "2024-01-15"

    def test_get_last_viewed_date_no_referer(self) -> None:
        """get_last_viewed_date関数のテスト（Refererなし）"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        
        with patch('app.utils.calendar_utils.get_today_formatted') as mock_today:
            mock_today.return_value = "2024-01-15"
            result = get_last_viewed_date(mock_request)
            assert result == "2024-01-15"

    def test_get_last_viewed_date_no_api_day(self) -> None:
        """get_last_viewed_date関数のテスト（API日付なし）"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "http://localhost:8000/other/path"
        
        with patch('app.utils.calendar_utils.get_today_formatted') as mock_today:
            mock_today.return_value = "2024-01-15"
            result = get_last_viewed_date(mock_request)
            assert result == "2024-01-15"


class TestMonthNavigation:
    """月ナビゲーション関連のテスト"""

    def test_get_prev_month_date_normal(self) -> None:
        """get_prev_month_date関数のテスト（通常）"""
        result = get_prev_month_date(2024, 5)
        assert result == datetime.date(2024, 4, 1)

    def test_get_prev_month_date_january(self) -> None:
        """get_prev_month_date関数のテスト（1月）"""
        result = get_prev_month_date(2024, 1)
        assert result == datetime.date(2023, 12, 1)

    def test_get_next_month_date_normal(self) -> None:
        """get_next_month_date関数のテスト（通常）"""
        result = get_next_month_date(2024, 5)
        assert result == datetime.date(2024, 6, 1)

    def test_get_next_month_date_december(self) -> None:
        """get_next_month_date関数のテスト（12月）"""
        result = get_next_month_date(2024, 12)
        assert result == datetime.date(2025, 1, 1)


class TestWeekOperations:
    """週操作関連のテスト"""

    @patch('app.utils.calendar_utils.datetime')
    def test_get_current_week_formatted(self, mock_datetime: Any) -> None:
        """get_current_week_formatted関数のテスト"""
        # 2024-01-15（月曜日）を設定
        mock_datetime.date.today.return_value = datetime.date(2024, 1, 15)
        result = get_current_week_formatted()
        assert result == "2024-01-15"

    def test_parse_week_valid(self) -> None:
        """parse_week関数のテスト（有効な週）"""
        result = parse_week("2024-01-15")
        assert result == datetime.date(2024, 1, 15)

    def test_parse_week_invalid(self) -> None:
        """parse_week関数のテスト（無効な週）"""
        with pytest.raises(ValueError):
            parse_week("invalid-week")

    def test_get_prev_week_date(self) -> None:
        """get_prev_week_date関数のテスト"""
        monday = datetime.date(2024, 1, 15)  # 月曜日
        result = get_prev_week_date(monday)
        assert result == datetime.date(2024, 1, 8)

    def test_get_next_week_date(self) -> None:
        """get_next_week_date関数のテスト"""
        monday = datetime.date(2024, 1, 15)  # 月曜日
        result = get_next_week_date(monday)
        assert result == datetime.date(2024, 1, 22)

    def test_format_week_name(self) -> None:
        """format_week_name関数のテスト"""
        monday = datetime.date(2024, 1, 15)
        result = format_week_name(monday)
        expected = "2024年1月第3週"
        assert result == expected

    def test_format_week_name_cross_month(self) -> None:
        """format_week_name関数のテスト（月跨ぎ）"""
        monday = datetime.date(2024, 1, 29)
        result = format_week_name(monday)
        expected = "2024年1月第5週"
        assert result == expected


class TestCalendarDataBuilding:
    """カレンダーデータ構築関連のテスト"""

    def setup_method(self) -> None:
        """テスト用のデータをセットアップ"""
        # テスト用の勤怠データ
        self.mock_user = MagicMock()
        self.mock_user.id = "test_user"
        self.mock_user.username = "テストユーザー"
        
        self.mock_location = MagicMock()
        self.mock_location.id = 1
        self.mock_location.name = "オフィス"
        
        self.attendance = MagicMock()
        self.attendance.id = 1
        self.attendance.user_id = "test_user"
        self.attendance.date = datetime.date(2024, 1, 15)
        self.attendance.location_id = 1
        self.attendance.note = "テストメモ"
        self.attendance.user = self.mock_user
        self.attendance.location = self.mock_location
        self.attendance.location_info = "オフィス"

        self.attendance_counts = {1: 5}
        self.location_types = ["オフィス", "リモート"]

    @patch('app.utils.calendar_utils.is_holiday')
    @patch('app.utils.calendar_utils.get_holiday_name')
    @patch('app.utils.calendar_utils.generate_location_data')
    def test_build_week_calendar_data(self, mock_generate_location_data: Any, mock_get_holiday_name: Any, mock_is_holiday: Any) -> None:
        """build_week_calendar_data関数のテスト"""
        mock_is_holiday.return_value = False
        mock_get_holiday_name.return_value = None
        mock_generate_location_data.return_value = [{"id": 1, "name": "オフィス", "count": 5}]
        
        result = build_week_calendar_data(
            "2024-01-15",
            [self.attendance],
            self.attendance_counts,
            self.location_types
        )
        
        assert "weeks" in result
        assert "week_name" in result
        assert "prev_week" in result
        assert "next_week" in result
        assert "locations" in result
        assert len(result["weeks"]) == 1
        assert len(result["weeks"][0]) == 7

    @patch('app.utils.calendar_utils.is_holiday')
    @patch('app.utils.calendar_utils.get_holiday_name')
    @patch('app.utils.calendar_utils.generate_location_data')
    def test_build_calendar_data(self, mock_generate_location_data: Any, mock_get_holiday_name: Any, mock_is_holiday: Any) -> None:
        """build_calendar_data関数のテスト"""
        mock_is_holiday.return_value = False
        mock_get_holiday_name.return_value = None
        mock_generate_location_data.return_value = [{"id": 1, "name": "オフィス", "count": 5}]
        
        result = build_calendar_data(
            "2024-01",
            [self.attendance],
            self.attendance_counts,
            self.location_types
        )
        
        assert "weeks" in result
        assert "month_name" in result
        assert "prev_month" in result
        assert "next_month" in result
        assert "locations" in result
        assert len(result["weeks"]) > 0

    @patch('app.utils.calendar_utils.is_holiday')
    @patch('app.utils.calendar_utils.get_holiday_name')
    def test_build_calendar_data_with_holiday(self, mock_get_holiday_name: Any, mock_is_holiday: Any) -> None:
        """build_calendar_data関数のテスト（祝日あり）"""
        mock_is_holiday.side_effect = lambda d: d.day == 1  # 1日を祝日に設定
        mock_get_holiday_name.side_effect = lambda d: "元日" if d.day == 1 else None
        
        with patch('app.utils.calendar_utils.generate_location_data') as mock_generate_location_data:
            mock_generate_location_data.return_value = []
            
            result = build_calendar_data(
                "2024-01",
                [],
                {},
                self.location_types
            )
            
            # 元日の情報を確認
            new_year_day = None
            for week in result["weeks"]:
                for day in week:
                    if day["day"] == 1:
                        new_year_day = day
                        break
            
            assert new_year_day is not None
            assert new_year_day["is_holiday"] is True
            assert new_year_day["holiday_name"] == "元日" 
