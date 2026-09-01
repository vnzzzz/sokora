"""Delete-error contract for master-management SSR/HTMX routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import models
from app.routers.pages import holiday as holiday_router
from app.services.errors import ApplicationError

pytestmark = pytest.mark.asyncio


async def test_holiday_delete_error_keeps_modal_and_renders_warning(
    async_client: AsyncClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_response = await async_client.post(
        "/holidays",
        data={"date": "2035-07-14", "name": "delete-error-holiday"},
    )
    assert created_response.status_code == 200

    holiday = (
        db.query(models.CustomHoliday)
        .filter(models.CustomHoliday.name == "delete-error-holiday")
        .one()
    )
    holiday_id = int(holiday.id)

    def raise_delete_error(*_args, **_kwargs) -> None:
        raise ApplicationError("削除できません")

    monkeypatch.setattr(
        holiday_router.custom_holiday_service,
        "delete_custom_holiday",
        raise_delete_error,
    )

    response = await async_client.delete(f"/holidays/{holiday_id}")

    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
    assert "削除できません" in response.text
    assert f'custom-holiday-delete-modal-{holiday_id}' in response.text
