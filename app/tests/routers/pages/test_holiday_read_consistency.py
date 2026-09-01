"""Custom holiday read consistency contracts for calendar adapters."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.custom_holiday import CustomHoliday

pytestmark = pytest.mark.asyncio


async def test_custom_holiday_reads_shared_db_snapshot_per_request(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    db = db_with_data
    target_date = date(2031, 5, 13)
    holiday = CustomHoliday(date=target_date, name="Replica Holiday Before")
    db.add(holiday)
    db.commit()

    first = await async_client.get("/calendar?month=2031-05")
    assert first.status_code == 200
    assert "Replica Holiday Before" in first.text

    holiday.name = "Replica Holiday After"
    db.add(holiday)
    db.commit()

    second = await async_client.get("/calendar?month=2031-05")
    assert second.status_code == 200
    assert "Replica Holiday After" in second.text
    assert "Replica Holiday Before" not in second.text

    weekly = await async_client.get("/attendance/weekly?week=2031-05-12")
    assert weekly.status_code == 200
    assert "Replica Holiday After" in weekly.text
