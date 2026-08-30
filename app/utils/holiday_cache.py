"""
祝日データキャッシュ管理
======================

ビルド時に取得した祝日データをローカルファイルから読み込み、DBのカスタム祝日とマージします。
運用時にはAPIアクセスを行いません。
"""

import json
import datetime
from typing import Dict, Any
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import logger
from app import crud

# キャッシュファイルのパス
ASSETS_JSON_DIR = Path(__file__).parent.parent.parent / "assets" / "json"
CACHE_FILE = ASSETS_JSON_DIR / "holidays_cache.json"


class HolidayCache:
    """祝日データのキャッシュ管理クラス（読み取り専用）"""

    def __init__(self) -> None:
        self._file_cache: Dict[str, str] = {}
        self._custom_cache: Dict[str, str] = {}
        self._cache: Dict[str, str] = {}
        self._build_time_cache: bool = False
        self._load_cache()

    def _merge_cache(self) -> None:
        """ビルド時キャッシュとカスタム祝日をマージする"""
        self._cache = {**self._file_cache, **self._custom_cache}

    def _load_cache(self) -> None:
        """ビルド時キャッシュファイルからデータを読み込む"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._file_cache = data.get("holidays", {})
                    self._build_time_cache = data.get("build_time", False)

                    if self._build_time_cache:
                        logger.info(f"ビルド時祝日キャッシュを読み込みました: {len(self._file_cache)}件")
                    else:
                        logger.warning("レガシーキャッシュファイルを読み込みました。ビルド時キャッシュの作成を推奨します。")
            else:
                logger.error(f"祝日キャッシュファイルが見つかりません: {CACHE_FILE}")
                logger.error("コンテナビルド時に祝日データの取得が失敗した可能性があります。")
                self._file_cache = {}
        except Exception as e:
            logger.error(f"祝日キャッシュの読み込みに失敗しました: {e}")
            self._file_cache = {}
        finally:
            self._merge_cache()

    def refresh_from_db(self, db: Session) -> None:
        """DB上のカスタム祝日を読み込み、キャッシュを更新する"""
        try:
            custom_holidays = crud.custom_holiday.get_all(db)
            self._custom_cache = {
                holiday.date.strftime("%Y-%m-%d"): str(holiday.name) for holiday in custom_holidays
            }
            logger.info(f"カスタム祝日を読み込みました: {len(self._custom_cache)}件")
        except Exception as e:
            logger.error(f"カスタム祝日の読み込みに失敗しました: {e}", exc_info=True)
            self._custom_cache = {}
        finally:
            self._merge_cache()

    def is_holiday(self, date_obj: datetime.date) -> bool:
        """指定日が祝日かどうかを判定する"""
        date_str = date_obj.strftime("%Y-%m-%d")
        return date_str in self._cache

    def get_holiday_name(self, date_obj: datetime.date) -> str:
        """指定日の祝日名を取得する"""
        date_str = date_obj.strftime("%Y-%m-%d")
        return self._cache.get(date_str, "")

    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュの情報を取得する（デバッグ用）"""
        return {
            "total_holidays": len(self._cache),
            "build_time_cache": self._build_time_cache,
            "cache_file_exists": CACHE_FILE.exists(),
            "years_covered": sorted(list(set(date[:4] for date in self._cache.keys()))) if self._cache else [],
            "custom_total": len(self._custom_cache),
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


def refresh_holiday_cache(db: Session) -> None:
    """DBのカスタム祝日を反映してキャッシュを更新する"""
    _holiday_cache.refresh_from_db(db)
