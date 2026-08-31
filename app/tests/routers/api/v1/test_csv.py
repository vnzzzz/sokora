"""CSV download contract tests."""

import csv
import io
from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient

from app.tests.routers.api.v1.test_attendance import (
    create_test_group_via_api,
    create_test_location_via_api,
    create_test_user_type_via_api,
    create_test_user_via_api,
)

pytestmark = pytest.mark.asyncio


async def test_download_csv_contains_json_api_attendance(
    async_client: AsyncClient,
) -> None:
    group_id = await create_test_group_via_api(async_client, "CSV Group")
    user_type_id = await create_test_user_type_via_api(async_client, "CSV User Type")
    user_id = await create_test_user_via_api(
        async_client,
        "csv-user",
        "CSV User",
        group_id,
        user_type_id,
    )
    location_id = await create_test_location_via_api(async_client, "CSV Location")
    attendance_date = date(2032, 5, 6)
    created = await async_client.post(
        "/api/v1/attendances",
        json={
            "user_id": user_id,
            "date": attendance_date.isoformat(),
            "location_id": location_id,
        },
    )
    assert created.status_code == status.HTTP_201_CREATED

    response = await async_client.get("/api/v1/csv/download?month=2032-05")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        'filename="work_entries_2032-05.csv"' in response.headers["content-disposition"]
    )
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:4] == ["user_name", "user_id", "group_name", "user_type"]
    user_row = next(row for row in rows[1:] if row[1] == user_id)
    target_header = attendance_date.strftime("%Y/%m/%d")
    target_index = rows[0].index(target_header)
    assert user_row[target_index] == "CSV Location"


async def test_download_csv_supports_sjis(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/csv/download?encoding=sjis")
    assert response.status_code == status.HTTP_200_OK
    assert "shift_jis" in response.headers["content-type"].lower()
    response.content.decode("shift_jis")


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("month=2032-13", "月の形式が無効です"),
        ("encoding=latin1", "無効なエンコーディングです"),
    ],
)
async def test_download_csv_rejects_invalid_query(
    async_client: AsyncClient,
    query: str,
    detail: str,
) -> None:
    response = await async_client.get(f"/api/v1/csv/download?{query}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert detail in response.json()["detail"]
