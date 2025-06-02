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
    HolidayCache, is_holiday, get_holiday_name, get_cache_info, CACHE_DIR, CACHE_FILE
)


class TestHolidayCache:
    """HolidayCacheクラスのテスト"""

    def setup_method(self) -> None:
        """テスト用のセットアップ"""
        # 各テストで新しいインスタンスを作成
        pass

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_existing_build_time_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（ビルド時キャッシュあり）"""
        # モックデータ
        cache_data = {
            'holidays': {
                '2024-01-01': '元日',
                '2024-05-03': '憲法記念日'
            },
            'build_time': True
        }
        
        mock_cache_file.exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            holiday_cache = HolidayCache()
            
            assert holiday_cache._cache == cache_data['holidays']
            assert holiday_cache._build_time_cache is True

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_existing_legacy_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（レガシーキャッシュあり）"""
        # モックデータ（build_timeフラグなし）
        cache_data = {
            'holidays': {
                '2024-01-01': '元日',
                '2024-05-03': '憲法記念日'
            }
        }
        
        mock_cache_file.exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            holiday_cache = HolidayCache()
            
            assert holiday_cache._cache == cache_data['holidays']
            assert holiday_cache._build_time_cache is False

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_no_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（キャッシュなし）"""
        mock_cache_file.exists.return_value = False
        
        holiday_cache = HolidayCache()
        
        assert holiday_cache._cache == {}
        assert holiday_cache._build_time_cache is False

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_init_with_invalid_cache(self, mock_cache_file: Any) -> None:
        """HolidayCache.__init__のテスト（無効なキャッシュ）"""
        mock_cache_file.exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data="invalid json")):
            holiday_cache = HolidayCache()
            
            assert holiday_cache._cache == {}
            assert holiday_cache._build_time_cache is False

    def test_is_holiday_true(self) -> None:
        """is_holiday関数のテスト（祝日）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 1)
        result = holiday_cache.is_holiday(test_date)
        
        assert result is True

    def test_is_holiday_false(self) -> None:
        """is_holiday関数のテスト（平日）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 2)
        result = holiday_cache.is_holiday(test_date)
        
        assert result is False

    def test_get_holiday_name_exists(self) -> None:
        """get_holiday_name関数のテスト（祝日名あり）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 1)
        result = holiday_cache.get_holiday_name(test_date)
        
        assert result == '元日'

    def test_get_holiday_name_not_exists(self) -> None:
        """get_holiday_name関数のテスト（祝日名なし）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {'2024-01-01': '元日'}
        
        test_date = datetime.date(2024, 1, 2)
        result = holiday_cache.get_holiday_name(test_date)
        
        assert result == ""

    @patch('app.utils.holiday_cache.CACHE_FILE')
    def test_get_cache_info(self, mock_cache_file: Any) -> None:
        """get_cache_info関数のテスト"""
        mock_cache_file.exists.return_value = True
        
        holiday_cache = HolidayCache()
        holiday_cache._cache = {
            '2024-01-01': '元日',
            '2024-05-03': '憲法記念日',
            '2025-01-01': '元日'
        }
        holiday_cache._build_time_cache = True
        
        result = holiday_cache.get_cache_info()
        
        assert result['total_holidays'] == 3
        assert result['build_time_cache'] is True
        assert result['cache_file_exists'] is True
        assert '2024' in result['years_covered']
        assert '2025' in result['years_covered']

    def test_get_cache_info_empty_cache(self) -> None:
        """get_cache_info関数のテスト（空のキャッシュ）"""
        holiday_cache = HolidayCache()
        holiday_cache._cache = {}
        holiday_cache._build_time_cache = False
        
        result = holiday_cache.get_cache_info()
        
        assert result['total_holidays'] == 0
        assert result['build_time_cache'] is False
        assert result['years_covered'] == []


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

    @patch('app.utils.holiday_cache._holiday_cache')
    def test_get_cache_info_function(self, mock_holiday_cache: Any) -> None:
        """get_cache_info関数のテスト"""
        expected_info = {
            'total_holidays': 10,
            'build_time_cache': True,
            'cache_file_exists': True,
            'years_covered': ['2024', '2025']
        }
        mock_holiday_cache.get_cache_info.return_value = expected_info
        
        result = get_cache_info()
        
        assert result == expected_info
        mock_holiday_cache.get_cache_info.assert_called_once()


class TestIntegration:
    """統合テスト"""

    def test_end_to_end_holiday_check(self) -> None:
        """エンドツーエンドの祝日チェックテスト"""
        # 実際の祝日データを模擬
        cache_data = {
            'holidays': {
                '2024-01-01': '元日',
                '2024-01-08': '成人の日',
                '2024-02-11': '建国記念の日',
                '2024-02-12': '建国記念の日 振替休日',
                '2024-02-23': '天皇誕生日',
                '2024-03-20': '春分の日',
                '2024-04-29': '昭和の日',
                '2024-05-03': '憲法記念日',
                '2024-05-04': 'みどりの日',
                '2024-05-05': 'こどもの日',
                '2024-05-06': 'こどもの日 振替休日'
            },
            'build_time': True
        }
        
        # 専用のHolidayCacheインスタンスを作成してテストする
        with patch('app.utils.holiday_cache.CACHE_FILE') as mock_cache_file:
            mock_cache_file.exists.return_value = True
            
            with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
                # 新しいインスタンスを作成してテスト
                test_cache = HolidayCache()
                
                # 祝日チェック
                assert test_cache.is_holiday(datetime.date(2024, 1, 1)) is True  # 元日
                assert test_cache.get_holiday_name(datetime.date(2024, 1, 1)) == '元日'
                
                assert test_cache.is_holiday(datetime.date(2024, 5, 3)) is True  # 憲法記念日
                assert test_cache.get_holiday_name(datetime.date(2024, 5, 3)) == '憲法記念日'
                
                # 平日チェック
                assert test_cache.is_holiday(datetime.date(2024, 1, 2)) is False
                assert test_cache.get_holiday_name(datetime.date(2024, 1, 2)) == ""
                
                # キャッシュ情報チェック
                info = test_cache.get_cache_info()
                assert info['total_holidays'] == 11
                assert info['build_time_cache'] is True 