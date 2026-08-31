import pytest
from httpx import AsyncClient

from app.services.errors import DataIntegrityError


@pytest.mark.asyncio
async def test_integrity_conflict_is_returned_as_409_without_db_error_details(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_integrity_conflict(*_args, **_kwargs):
        raise DataIntegrityError("同一ユーザー・日付の勤怠が競合しました")

    monkeypatch.setattr(
        "app.routers.api.v1.attendance.attendance_service.create_attendance",
        raise_integrity_conflict,
    )

    response = await async_client.post(
        "/api/v1/attendances",
        data={
            "user_id": "race-user",
            "date": "2030-01-01",
            "location_id": "1",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "同一ユーザー・日付の勤怠が競合しました"}
    assert "IntegrityError" not in response.text
    assert "sqlalchemy" not in response.text.lower()
