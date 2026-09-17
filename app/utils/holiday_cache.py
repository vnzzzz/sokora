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

ASSETS_JSON_DIR = Path(__file__).parent.parent.parent / "assets" / "json"
CACHE_FILE = ASSETS_JSON_DIR / "holidays_cache.json"

_EMPTY_CUSTOM_HOLIDAYS: Mapping[str, str] = MappingProxyType({})
_custom_holiday_snapshot: ContextVar[Mapping[str, str]] = ContextVar(
    "custom_holiday_snapshot",
    default=_EMPTY_CUSTOM_HOLIDAYS,
)


class HolidayCache:
    """production imageに含まれる標準祝日assetをprocess-localで読み取るcache。

    このcacheへ入るのはbuild時に固定した標準祝日だけで、DBから変更できるcustom holidayは
    保持しない。同一imageを使うreplica間で標準祝日を一致させつつ、mutableなDB stateを
    process-localへ複製しないための責務分離である。

    assetが読めない場合は空cacheへ縮退してapplication startup自体は継続する。failureはlogへ
    残すため、operatorはbuild artifactの欠落として診断する。
    """

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._build_time_cache: bool = False
        self._load_cache()

    def _load_cache(self) -> None:
        """build-time cache fileから標準祝日を読み込む。

        Returns:
            `None`。読み込み結果はinstance stateへ保持する。

        Notes:
            file不在/破損時は例外を外へ出さず空cacheへ縮退し、診断logを残す。
        """
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
        """標準祝日だけを使って指定日が祝日か判定する。

        Args:
            date_obj: 判定対象日。

        Returns:
            標準祝日cacheに名称が存在する場合`True`。
        """
        return self.get_holiday_name(date_obj) != ""

    def get_holiday_name(self, date_obj: datetime.date) -> str:
        """標準祝日cacheから指定日の名称を取得する。

        Args:
            date_obj: 取得対象日。

        Returns:
            祝日名。未登録の場合は空文字列。
        """
        date_str = date_obj.strftime("%Y-%m-%d")
        return self._cache.get(date_str, "")

    def get_cache_info(self) -> Dict[str, Any]:
        """immutableな標準祝日cacheの診断情報を返す。

        Returns:
            件数、build-time flag、file有無、対象年等のdiagnostic mapping。
        """
        return {
            "total_holidays": len(self._cache),
            "build_time_cache": self._build_time_cache,
            "cache_file_exists": CACHE_FILE.exists(),
            "years_covered": sorted({date[:4] for date in self._cache})
            if self._cache
            else [],
            # 診断viewの既存shapeを維持するためfieldだけ残す。custom holidayは共有DBを
            # request-local snapshotとして読むため、process cache上の件数は常に0になる。
            "custom_total": 0,
        }


# 標準祝日は同一production imageなら全replicaで同一内容になるimmutable data。
_holiday_cache = HolidayCache()


def bind_custom_holiday_snapshot(
    holidays: Mapping[str, str],
) -> Token[Mapping[str, str]]:
    """共有DBから読んだcustom holiday snapshotを現在contextへ束縛する。

    callerのmappingをcopyしてread-only viewにするため、束縛後のcaller側mutationは現在request
    の判定へ影響しない。返されたTokenは同じlogical contextで必ず
    :func:`reset_custom_holiday_snapshot` へ渡し、request終了後にsnapshotを漏らさないこと。

    ContextVarを使うことで同一process内の並行requestも別snapshotを持てるが、DB snapshotの
    読み取り時点そのものはcallerが所有する。

    Args:
        holidays: `YYYY-MM-DD`をkey、custom holiday名をvalueとするrequest snapshot。

    Returns:
        後でcontextを元へ戻すためのContextVar token。
    """
    return _custom_holiday_snapshot.set(MappingProxyType(dict(holidays)))


def reset_custom_holiday_snapshot(token: Token[Mapping[str, str]]) -> None:
    """対応するbind tokenをresetし、以前のcontext stateへ戻す。

    request dependencyは``finally``から呼び、template renderやDB readが例外終了した場合も
    次requestへcustom holidayを持ち越さない。

    Args:
        token: `bind_custom_holiday_snapshot()`が返した同一contextのtoken。
    """
    _custom_holiday_snapshot.reset(token)


def get_holiday_name(date_obj: datetime.date) -> str:
    """現在contextのcustom holidayを標準祝日より優先して名称を返す。

    同じ日付が両方に存在する場合はDB由来custom holidayをauthoritative overrideとして扱う。
    snapshotに日付が存在しない場合だけimmutableな標準祝日assetへfallbackする。

    Args:
        date_obj: 取得対象日。

    Returns:
        custom holidayまたは標準祝日の名称。未登録なら空文字列。
    """
    date_str = date_obj.strftime("%Y-%m-%d")
    custom_name = _custom_holiday_snapshot.get().get(date_str)
    if custom_name is not None:
        return custom_name
    return _holiday_cache.get_holiday_name(date_obj)


def is_holiday(date_obj: datetime.date) -> bool:
    """request-local custom holidayを含めて指定日が祝日か判定する。

    Args:
        date_obj: 判定対象日。

    Returns:
        custom/standardのいずれかに祝日名が存在する場合`True`。
    """
    return get_holiday_name(date_obj) != ""


def get_cache_info() -> Dict[str, Any]:
    """標準祝日cacheの診断情報を取得する。

    Returns:
        process-local標準祝日cacheのdiagnostic mapping。
    """
    return _holiday_cache.get_cache_info()
