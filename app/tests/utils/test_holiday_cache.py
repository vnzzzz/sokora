"""
holiday_cache のテストケース
"""

import pytest
import datetime
import json
import os
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from typing import Dict, Any

from app.utils.holiday_cache import (
    HolidayCache, is_holiday, get_holiday_name, CACHE_DIR, CACHE_FILE
)


class TestHolidayCache:
    """HolidayCacheクラスのテスト"""

    def setup_method(self) -> None:
        """テスト用のセットアップ"""
        # 各テストで新しいインスタンスを作成
        pass

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_existing_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（既存キャッシュあり）"""
        # モックデータ
        cache_data = {
            'holidays': {
                '2024-01-01': '元日',
                '2024-05-03': '憲法記念日'
            },
            'last_updated_year': 2024
        }
        
        mock_cache_file.exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            holiday_cache = HolidayCache()
            
            assert holiday_cache._cache == cache_data['holidays']
            assert holiday_cache._last_updated_year == 2024

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_no_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（キャッシュなし）"""
        mock_cache_file.exists.return_value = False
        
        holiday_cache = HolidayCache()
        
        assert holiday_cache._cache == {}
        assert holiday_cache._last_updated_year is None

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_invalid_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（無効なキャッシュ）"""
        mock_cache_file.exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data="invalid json")):
            holiday_cache = HolidayCache()
            
            assert holiday_cache._cache == {}
            assert holiday_cache._last_updated_year is None

    @patch('app.utils.holiday_cache.CACHE_DIR')
    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_save_cache(self, mock_cache_file: Any, mock_cache_dir: Any) -> None:
        """_save_cache関数のテスト"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        holiday_cache._last_updated_year = 2024
        
        mock_file_handle = mock_open()
        
        with patch('builtins.open', mock_file_handle):
            holiday_cache._save_cache()
            
            # ディレクトリ作成が呼ばれることを確認
            mock_cache_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            
            # ファイル書き込みが呼ばれることを確認
            mock_file_handle.assert_called_once()

    @patch('app.utils.holiday_cache.httpx.Client')
    def test_fetch_holidays_from_api_success(self, mock_client: Any) -> None:
        """_fetch_holidays_from_api関数のテスト（成功）"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            '2024-01-01': '元日',
            '2024-05-03': '憲法記念日'
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        holiday_cache = HolidayCache()
        result = holiday_cache._fetch_holidays_from_api(2024)
        
        assert result == {'2024-01-01': '元日', '2024-05-03': '憲法記念日'}
        mock_client_instance.get.assert_called_once_with(
            "https://holidays-jp.github.io/api/v1/2024/date.json"
        )

    @patch('app.utils.holiday_cache.httpx.Client')
    def test_fetch_holidays_from_api_error(self, mock_client: Any) -> None:
        """_fetch_holidays_from_api関数のテスト（エラー）"""
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = Exception("API Error")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        holiday_cache = HolidayCache()
        result = holiday_cache._fetch_holidays_from_api(2024)
        
        assert result == {}

    def test_should_update_cache_new_year(self) -> None:
        """_should_update_cache関数のテスト（新しい年）"""
        holiday_cache = HolidayCache()
        holiday_cache._last_updated_year = 2023
        holiday_cache._cache = {'2023-01-01': '元日'}
        
        result = holiday_cache._should_update_cache(2024)
        assert result is True

    def test_should_update_cache_same_year_with_data(self) -> None:
        """_should_update_cache関数のテスト（同年、データあり）"""
        holiday_cache = HolidayCache()
        holiday_cache._last_updated_year = 2024
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        result = holiday_cache._should_update_cache(2024)
        assert result is False

    def test_should_update_cache_same_year_no_data(self) -> None:
        """_should_update_cache関数のテスト（同年、データなし）"""
        holiday_cache = HolidayCache()
        holiday_cache._last_updated_year = 2024
        holiday_cache._cache = {'2023-01-01': '元日'}
        
        result = holiday_cache._should_update_cache(2024)
        assert result is True

    def test_should_update_cache_first_time(self) -> None:
        """_should_update_cache関数のテスト（初回）"""
        holiday_cache = HolidayCache()
        holiday_cache._last_updated_year = None
        
        result = holiday_cache._should_update_cache(2024)
        assert result is True

    @patch.object(HolidayCache, '_fetch_holidays_from_api')
    @patch.object(HolidayCache, '_save_cache')
    def test_update_cache_for_year(self, mock_save_cache: Any, mock_fetch_holidays: Any) -> None:
        """_update_cache_for_year関数のテスト"""
        holiday_cache = HolidayCache()
        holiday_cache._last_updated_year = None  # 強制的に更新が必要な状態にする
        
        # 年ごとの祝日データを模擬
        mock_fetch_holidays.side_effect = [
            {'2023-01-01': '元日'},  # 2023年
            {'2024-01-01': '元日', '2024-05-03': '憲法記念日'},  # 2024年
            {'2025-01-01': '元日'}   # 2025年
        ]
        
        holiday_cache._update_cache_for_year(2024)
        
        # 3年分のAPI呼び出しを確認
        assert mock_fetch_holidays.call_count == 3
        mock_fetch_holidays.assert_any_call(2023)
        mock_fetch_holidays.assert_any_call(2024)
        mock_fetch_holidays.assert_any_call(2025)
        
        # キャッシュの保存が呼ばれることを確認
        mock_save_cache.assert_called_once()
        
        # last_updated_yearが更新されることを確認
        assert holiday_cache._last_updated_year == 2024

    @patch.object(HolidayCache, '_update_cache_for_year')
    def test_is_holiday_true(self, mock_update_cache: Any) -> None:
        """is_holiday関数のテスト（祝日）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 1)
        result = holiday_cache.is_holiday(test_date)
        
        assert result is True
        mock_update_cache.assert_called_once_with(2024)

    @patch.object(HolidayCache, '_update_cache_for_year')
    def test_is_holiday_false(self, mock_update_cache: Any) -> None:
        """is_holiday関数のテスト（平日）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 2)
        result = holiday_cache.is_holiday(test_date)
        
        assert result is False
        mock_update_cache.assert_called_once_with(2024)

    @patch.object(HolidayCache, '_update_cache_for_year')
    def test_get_holiday_name_exists(self, mock_update_cache: Any) -> None:
        """get_holiday_name関数のテスト（祝日名あり）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 1)
        result = holiday_cache.get_holiday_name(test_date)
        
        assert result == '元日'
        mock_update_cache.assert_called_once_with(2024)

    @patch.object(HolidayCache, '_update_cache_for_year')
    def test_get_holiday_name_not_exists(self, mock_update_cache: Any) -> None:
        """get_holiday_name関数のテスト（祝日名なし）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 2)
        result = holiday_cache.get_holiday_name(test_date)
        
        assert result == ""
        mock_update_cache.assert_called_once_with(2024)


class TestGlobalFunctions:
    """グローバル関数のテスト"""

    @patch('app.utils.holiday_cache._holiday_cache')
    def test_is_holiday_function(self, mock_holiday_cache: Any) -> None:
        """is_holiday関数のテスト"""
        mock_holiday_cache.is_holiday.return_value = True
        
        test_date = datetime.date(2024, 1, 1)
        result = is_holiday(test_date)
        
        assert result is True
        mock_holiday_cache.is_holiday.assert_called_once_with(test_date)

    @patch('app.utils.holiday_cache._holiday_cache')
    def test_get_holiday_name_function(self, mock_holiday_cache: Any) -> None:
        """get_holiday_name関数のテスト"""
        mock_holiday_cache.get_holiday_name.return_value = '元日'
        
        test_date = datetime.date(2024, 1, 1)
        result = get_holiday_name(test_date)
        
        assert result == '元日'
        mock_holiday_cache.get_holiday_name.assert_called_once_with(test_date) 