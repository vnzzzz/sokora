"""
祝日データキャッシュ管理
======================

Holidays JP APIから祝日データを取得し、ローカルファイルにキャッシュする機能を提供します。
"""

import json
import os
import datetime
from typing import Dict, Optional
from pathlib import Path
import httpx

from app.core.config import logger

# キャッシュファイルのパス
CACHE_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "holidays_cache.json"

# Holidays JP API のベースURL
HOLIDAYS_API_BASE = "https://holidays-jp.github.io/api/v1"


class HolidayCache:
    """祝日データのキャッシュ管理クラス"""
    
    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._last_updated_year: Optional[int] = None
        self._load_cache()
    
    def _load_cache(self) -> None:
        """キャッシュファイルからデータを読み込む"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = data.get('holidays', {})
                    self._last_updated_year = data.get('last_updated_year')
                    logger.info(f"祝日キャッシュを読み込みました: {len(self._cache)}件")
        except Exception as e:
            logger.error(f"祝日キャッシュの読み込みに失敗しました: {e}")
            self._cache = {}
            self._last_updated_year = None
    
    def _save_cache(self) -> None:
        """キャッシュデータをファイルに保存する"""
        try:
            # ディレクトリが存在しない場合は作成
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {
                'holidays': self._cache,
                'last_updated_year': self._last_updated_year,
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"祝日キャッシュを保存しました: {len(self._cache)}件")
        except Exception as e:
            logger.error(f"祝日キャッシュの保存に失敗しました: {e}")
    
    def _fetch_holidays_from_api(self, year: int) -> Dict[str, str]:
        """指定年の祝日データをAPIから取得する"""
        try:
            url = f"{HOLIDAYS_API_BASE}/{year}/date.json"
            logger.info(f"祝日データを取得中: {url}")
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                
                holidays = response.json()
                logger.info(f"{year}年の祝日データを取得しました: {len(holidays)}件")
                return holidays
                
        except Exception as e:
            logger.error(f"{year}年の祝日データ取得に失敗しました: {e}")
            return {}
    
    def _should_update_cache(self, year: int) -> bool:
        """キャッシュを更新すべきかどうかを判定する"""
        # 初回アクセスまたは年が変わった場合は更新
        if self._last_updated_year is None or self._last_updated_year != year:
            return True
        
        # 指定年の祝日データがキャッシュに存在しない場合は更新
        year_str = str(year)
        has_year_data = any(date.startswith(year_str) for date in self._cache.keys())
        return not has_year_data
    
    def _update_cache_for_year(self, year: int) -> None:
        """指定年の祝日データでキャッシュを更新する"""
        if not self._should_update_cache(year):
            return
        
        # 前年、当年、翌年のデータを取得
        years_to_fetch = [year - 1, year, year + 1]
        
        for fetch_year in years_to_fetch:
            holidays = self._fetch_holidays_from_api(fetch_year)
            if holidays:
                # 既存のその年のデータを削除
                year_str = str(fetch_year)
                keys_to_remove = [key for key in self._cache.keys() if key.startswith(year_str)]
                for key in keys_to_remove:
                    del self._cache[key]
                
                # 新しいデータを追加
                self._cache.update(holidays)
        
        self._last_updated_year = year
        self._save_cache()
    
    def is_holiday(self, date_obj: datetime.date) -> bool:
        """指定日が祝日かどうかを判定する"""
        # 必要に応じてキャッシュを更新
        self._update_cache_for_year(date_obj.year)
        
        date_str = date_obj.strftime('%Y-%m-%d')
        return date_str in self._cache
    
    def get_holiday_name(self, date_obj: datetime.date) -> str:
        """指定日の祝日名を取得する"""
        # 必要に応じてキャッシュを更新
        self._update_cache_for_year(date_obj.year)
        
        date_str = date_obj.strftime('%Y-%m-%d')
        return self._cache.get(date_str, "")


# グローバルインスタンス
_holiday_cache = HolidayCache()


def is_holiday(date_obj: datetime.date) -> bool:
    """指定日が祝日かどうかを判定する
    
    Args:
        date_obj: 判定する日付
    
    Returns:
        bool: 祝日の場合はTrue、そうでない場合はFalse
    """
    return _holiday_cache.is_holiday(date_obj)


def get_holiday_name(date_obj: datetime.date) -> str:
    """指定日の祝日名を取得する
    
    Args:
        date_obj: 判定する日付
    
    Returns:
        str: 祝日名（祝日でない場合は空文字列）
    """
    return _holiday_cache.get_holiday_name(date_obj) 