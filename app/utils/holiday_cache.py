"""
祝日データキャッシュ管理
======================

ビルド時に取得した標準祝日データをローカルファイルから読み込みます。
標準祝日はproduction imageに含まれるimmutable assetとしてprocess-localに保持し、
DB由来のカスタム祝日はrequest-local snapshotで上書きします。
"""

import datetime
import json
from contextvars import ContextVar, Token
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Mapping

from app.core.config import logger

# キャッシュファイルのパス
ASSETS_JSON_DIR = Path(__file__).parent.parent.parent / "assets" / "json"
CACHE_FILE = ASSETS_JSON_DIR / "holidays_cache.json"

_EMPTY_CUSTOM_HOLIDAYS: Mapping[str, str] = MappingProxyType({})
_custom_holiday_snapshot: ContextVar[Mapping[str, str]] = ContextVar(
    "custom_holiday_snapshot",
    default=_EMPTY_CUSTOM_HOLIDAYS,
)


class HolidayCache:
    """production imageに含まれる標準祝日データの読み取り専用cache。"""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._build_time_cache: bool = False
        self._load_cache()

    def _load_cache(self) -> None:
        """ビルド時キャッシュファイルから標準祝日データを読み込む。"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = data.get("holidays", {})
                    self._build_time_cache = data.get("build_time", False)

                    if self._build_time_cache:
                        logger.info(
                            "ビルド時祝日キャッシュを読み込みました: %s件",
                            len(self._cache),
                        )
                    else:
                        logger.warning(
                            "レガシーキャッシュファイルを読み込みました。"
                            "ビルド時キャッシュの作成を推奨します。"
                        )
            else:
                logger.error("祝日キャッシュファイルが見つかりません: %s", CACHE_FILE)
                logger.error(
                    "コンテナビルド時に祝日データの取得が失敗した可能性があります。"
                )
                self._cache = {}
        except Exception as exc:
            logger.error("祝日キャッシュの読み込みに失敗しました: %s", exc)
            self._cache = {}

    def is_holiday(self, date_obj: datetime.date) -> bool:
        """標準祝日データだけを使って指定日が祝日か判定する。"""
        return self.get_holiday_name(date_obj) != ""

    def get_holiday_name(self, date_obj: datetime.date) -> str:
        """標準祝日データから指定日の名称を取得する。"""
        date_str = date_obj.strftime("%Y-%m-%d")
        return self._cache.get(date_str, "")

    def get_cache_info(self) -> Dict[str, Any]:
        """immutableな標準祝日cacheの診断情報を返す。"""
        return {
            "total_holidays": len(self._cache),
            "build_time_cache": self._build_time_cache,
            "cache_file_exists": CACHE_FILE.exists(),
            "years_covered": sorted({date[:4] for date in self._cache})
            if self._cache
            else [],
            # 互換用。DB由来custom holidayはこのprocess cacheには保持しない。
            "custom_total": 0,
        }


# 標準祝日は同一production imageなら全replicaで同一内容になるimmutable data。
_holiday_cache = HolidayCache()


def bind_custom_holiday_snapshot(
    holidays: Mapping[str, str],
) -> Token[Mapping[str, str]]:
    """共有DBから読んだcustom holidayを現在requestのcontextへ束縛する。"""
    return _custom_holiday_snapshot.set(MappingProxyType(dict(holidays)))


def reset_custom_holiday_snapshot(token: Token[Mapping[str, str]]) -> None:
    """request終了時にcustom holiday snapshotを破棄する。"""
    _custom_holiday_snapshot.reset(token)


def get_holiday_name(date_obj: datetime.date) -> str:
    """request-local custom holidayを優先して祝日名を返す。"""
    date_str = date_obj.strftime("%Y-%m-%d")
    custom_name = _custom_holiday_snapshot.get().get(date_str)
    if custom_name is not None:
        return custom_name
    return _holiday_cache.get_holiday_name(date_obj)


def is_holiday(date_obj: datetime.date) -> bool:
    """request-local custom holidayを含めて指定日が祝日か判定する。"""
    return get_holiday_name(date_obj) != ""


def get_cache_info() -> Dict[str, Any]:
    """標準祝日cacheの診断情報を取得する。"""
    return _holiday_cache.get_cache_info()
