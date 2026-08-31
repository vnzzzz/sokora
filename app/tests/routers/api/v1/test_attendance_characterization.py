"""Attendance HTMX page adapter characterization tests."""

import json
from datetime import date

from fastapi import status
from httpx import AsyncClient, Response

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
) -> None:
    monday = attendance_date.fromordinal(
        attendance_date.toordinal() - attendance_date.weekday()
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert json.loads(response.headers["HX-Trigger"]) == {
        "closeModal": f"attendance-modal-{user_id}-{attendance_date.isoformat()}",
        "refreshUserAttendance": {
            "user_id": user_id,
            "month": attendance_date.strftime("%Y-%m"),
            "week": monday.isoformat(),
        },
        "refreshAttendance": {
            "month": attendance_date.strftime("%Y-%m"),
            "week": monday.isoformat(),
        },
    }


async def _references(async_client: AsyncClient) -> tuple[str, int, int]:
    group_id = await create_test_group_via_api(async_client, "HTMX Group")
    user_type_id = await create_test_user_type_via_api(async_client, "HTMX User Type")
    user_id = await create_test_user_via_api(
        async_client,
        "htmx-user",
        "HTMX User",
        group_id,
        user_type_id,
    )
    first_location_id = await create_test_location_via_api(
        async_client, "HTMX Location A"
    )
    second_location_id = await create_test_location_via_api(
        async_client, "HTMX Location B"
    )
    return user_id, first_location_id, second_location_id


async def test_htmx_mutations_preserve_refresh_contract_without_referer(
    async_client: AsyncClient,
) -> None:
    user_id, first_location_id, second_location_id = await _references(async_client)
    attendance_date = date(2024, 12, 18)

    create_response = await async_client.post(
        "/attendance/entries",
        data={
            "user_id": user_id,
            "date": attendance_date.isoformat(),
            "location_id": str(first_location_id),
            "note": "created",
        },
    )
    assert_attendance_refresh_contract(
        create_response,
        user_id=user_id,
        attendance_date=attendance_date,
    )

    records = (await async_client.get("/api/v1/attendances")).json()["records"]
    attendance_id = next(
        int(record["id"])
        for record in records
        if record["user_id"] == user_id
        and record["date"] == attendance_date.isoformat()
    )

    update_response = await async_client.put(
        f"/attendance/entries/{attendance_id}",
        data={"location_id": str(second_location_id), "note": "updated"},
    )
    assert_attendance_refresh_contract(
        update_response,
        user_id=user_id,
        attendance_date=attendance_date,
    )

    delete_response = await async_client.delete(
        f"/attendance/entries/{attendance_id}"
    )
    assert_attendance_refresh_contract(
        delete_response,
        user_id=user_id,
        attendance_date=attendance_date,
    )


async def test_htmx_error_is_html_fragment_retargeted_into_modal(
    async_client: AsyncClient,
) -> None:
    user_id, location_id, _ = await _references(async_client)
    payload = {
        "user_id": user_id,
        "date": "2024-12-18",
        "location_id": str(location_id),
    }
    first = await async_client.post("/attendance/entries", data=payload)
    second = await async_client.post("/attendance/entries", data=payload)

    assert first.status_code == status.HTTP_204_NO_CONTENT
    assert second.status_code == status.HTTP_200_OK
    assert second.headers["content-type"].startswith("text/html")
    assert second.headers["HX-Retarget"] == "#attendance-form-error"
    assert second.headers["HX-Reswap"] == "innerHTML"
    assert "既に勤怠データが存在します" in second.text


async def test_htmx_write_routes_are_not_in_openapi(async_client: AsyncClient) -> None:
    schema = (await async_client.get("/openapi.json")).json()
    assert "/api/v1/attendances" in schema["paths"]
    assert all(not path.startswith("/attendance/entries") for path in schema["paths"])
