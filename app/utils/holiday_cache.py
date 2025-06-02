"""
祝日データキャッシュ管理
======================

ビルド時に取得した祝日データをローカルファイルから読み込む機能を提供します。
運用時にはAPIアクセスを行いません。
"""

import json
import datetime
from typing import Dict, Optional, Any
from pathlib import Path

from app.core.config import logger

# キャッシュファイルのパス
CACHE_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "holidays_cache.json"


class HolidayCache:
    """祝日データのキャッシュ管理クラス（読み取り専用）"""
    
    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._build_time_cache: bool = False
        self._load_cache()
    
    def _load_cache(self) -> None:
        """キャッシュファイルからデータを読み込む"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = data.get('holidays', {})
                    self._build_time_cache = data.get('build_time', False)
                    
                    if self._build_time_cache:
                        logger.info(f"ビルド時祝日キャッシュを読み込みました: {len(self._cache)}件")
                    else:
                        logger.warning("レガシーキャッシュファイルを読み込みました。ビルド時キャッシュの作成を推奨します。")
            else:
                logger.error(f"祝日キャッシュファイルが見つかりません: {CACHE_FILE}")
                logger.error("コンテナビルド時に祝日データの取得が失敗した可能性があります。")
        except Exception as e:
            logger.error(f"祝日キャッシュの読み込みに失敗しました: {e}")
            self._cache = {}
    
    def is_holiday(self, date_obj: datetime.date) -> bool:
        """指定日が祝日かどうかを判定する"""
        date_str = date_obj.strftime('%Y-%m-%d')
        return date_str in self._cache
    
    def get_holiday_name(self, date_obj: datetime.date) -> str:
        """指定日の祝日名を取得する"""
        date_str = date_obj.strftime('%Y-%m-%d')
        return self._cache.get(date_str, "")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュの情報を取得する（デバッグ用）"""
        return {
            'total_holidays': len(self._cache),
            'build_time_cache': self._build_time_cache,
            'cache_file_exists': CACHE_FILE.exists(),
            'years_covered': sorted(list(set(date[:4] for date in self._cache.keys()))) if self._cache else []
        }


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


def get_cache_info() -> Dict[str, Any]:
    """キャッシュの情報を取得する（デバッグ用）
    
    Returns:
        Dict[str, Any]: キャッシュ情報
    """
    return _holiday_cache.get_cache_info() 