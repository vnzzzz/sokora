"""Page read dependencies shared across SSR adapters."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.crud.custom_holiday import custom_holiday as custom_holiday_crud
from app.db.session import get_db
from app.utils.holiday_cache import (
    bind_custom_holiday_snapshot,
    reset_custom_holiday_snapshot,
)


async def bind_custom_holiday_read_snapshot(
    db: Session = Depends(get_db),
) -> AsyncGenerator[None, None]:
    """共有DBのcustom holidayを1 requestだけholiday resolverへ束縛する。

    標準祝日はproduction image内のimmutable assetを利用する一方、管理画面で
    更新可能なcustom holidayはprocess-global cacheへ複製しない。holidayを描画する
    requestごとに共有DBを読み、ContextVarへ束縛することで別replicaのwriteを次の
    readから観測できるようにする。
    """
    holidays = await run_in_threadpool(custom_holiday_crud.get_all, db)
    snapshot = {
        holiday.date.strftime("%Y-%m-%d"): str(holiday.name) for holiday in holidays
    }
    token = bind_custom_holiday_snapshot(snapshot)
    try:
        yield
    finally:
        reset_custom_holiday_snapshot(token)
