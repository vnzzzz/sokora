import json
from datetime import date

from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.orm import Session

from app.crud.attendance import attendance
from app.tests.routers.api.v1.test_attendance import (
    create_test_group_via_api,
    create_test_location_via_api,
    create_test_user_type_via_api,
    create_test_user_via_api,
)


def assert_attendance_refresh_contract(
    response: Response,
    *,
    user_id: str,
    attendance_date: date,
    month: str,
    week: str,
) -> None:
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert json.loads(response.headers["HX-Trigger"]) == {
        "closeModal": f"attendance-modal-{user_id}-{attendance_date.isoformat()}",
        "refreshUserAttendance": {
            "user_id": user_id,
            "month": month,
            "week": week,
        },
        "refreshAttendance": {
            "month": month,
            "week": week,
        },
    }


async def test_attendance_mutations_preserve_htmx_refresh_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    group_id = await create_test_group_via_api(async_client, "Characterization Group")
    user_type_id = await create_test_user_type_via_api(
        async_client, "Characterization User Type"
    )
    user_id = await create_test_user_via_api(
        async_client,
        "characterization-user",
        "Characterization User",
        group_id,
        user_type_id,
    )
    first_location_id = await create_test_location_via_api(
        async_client, "Characterization Location A"
    )
    second_location_id = await create_test_location_via_api(
        async_client, "Characterization Location B"
    )

    attendance_date = date(2024, 12, 18)
    month = "2024-12"
    week = "2024-12-16"
    headers = {"Referer": f"http://test/attendance/monthly?month={month}&week={week}"}

    create_response = await async_client.post(
        "/api/v1/attendances",
        data={
            "user_id": user_id,
            "date": attendance_date.isoformat(),
            "location_id": str(first_location_id),
            "note": "created",
        },
        headers=headers,
    )
    assert_attendance_refresh_contract(
        create_response,
        user_id=user_id,
        attendance_date=attendance_date,
        month=month,
        week=week,
    )

    attendance_obj = attendance.get_by_user_and_date(
        db,
        user_id=user_id,
        date=attendance_date,
    )
    assert attendance_obj is not None

    update_response = await async_client.put(
        f"/api/v1/attendances/{attendance_obj.id}",
        data={"location_id": str(second_location_id), "note": "updated"},
        headers=headers,
    )
    assert_attendance_refresh_contract(
        update_response,
        user_id=user_id,
        attendance_date=attendance_date,
        month=month,
        week=week,
    )

    delete_response = await async_client.delete(
        f"/api/v1/attendances/{attendance_obj.id}",
        headers=headers,
    )
    assert_attendance_refresh_contract(
        delete_response,
        user_id=user_id,
        attendance_date=attendance_date,
        month=month,
        week=week,
    )
    assert (
        attendance.get_by_user_and_date(db, user_id=user_id, date=attendance_date)
        is None
    )
