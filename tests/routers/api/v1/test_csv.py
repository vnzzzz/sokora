"""
CSVダウンロードAPIエンドポイント (/api/csv/download) のテスト
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta # test_download_csv_no_data で使用
import csv
import io
import calendar

pytestmark = pytest.mark.asyncio

# --- Helper Functions (test_attendance.py からコピー/一部修正) ---
# Note: 本来は共通の test utils に置くべきだが、今回は簡略化のためここに配置

async def create_test_user_via_api(async_client: AsyncClient, user_id: str, username: str, group_id: int, user_type_id: int) -> str:
    """API経由でテストユーザーを作成するヘルパー"""
    user_payload = {
        "user_id": user_id,
        "username": username,
        "group_id": group_id,
        "user_type_id": user_type_id
    }
    response = await async_client.post("/api/users", json=user_payload)
    assert response.status_code == status.HTTP_200_OK # 作成成功を確認
    return response.json()["id"]

async def create_test_location_via_api(async_client: AsyncClient, name: str) -> int:
    """API経由でテスト勤務場所を作成するヘルパー"""
    location_payload = {"name": name}
    response = await async_client.post("/api/locations", json=location_payload)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["id"]

async def create_test_group_via_api(async_client: AsyncClient, name: str) -> int:
    """API経由でテストグループを作成するヘルパー"""
    group_payload = {"name": name}
    response = await async_client.post("/api/groups", json=group_payload)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["id"]

async def create_test_user_type_via_api(async_client: AsyncClient, name: str) -> int:
    """API経由でテストユーザー種別を作成するヘルパー"""
    user_type_payload = {"name": name}
    response = await async_client.post("/api/user_types", json=user_type_payload)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["id"]

# --- GET /api/csv/download Tests --- 

async def test_download_csv_success_all(async_client: AsyncClient) -> None:
    """月指定なしでCSVが正常にダウンロードされることをテストします (UTF-8)。"""
    # データ準備
    group_id = await create_test_group_via_api(async_client, "CsvTestGroupAll")
    user_type_id = await create_test_user_type_via_api(async_client, "CsvTestUserTypeAll")
    user_id = await create_test_user_via_api(async_client, "csv_user_all", "Csv User All", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "CsvTestLocation All")
    
    test_date = date.today().isoformat()
    await async_client.post("/api/attendances", data={"user_id": user_id, "date": test_date, "location_id": str(location_id)})

    response = await async_client.get("/api/csv/download")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=\"work_entries.csv\"" in response.headers["content-disposition"]

    # CSV内容の検証
    csv_content = response.text
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) >= 2 # ヘッダー + 少なくとも1データ行
    header = rows[0]
    assert header[0] == "user_name"
    assert header[1] == "user_id"
    assert header[2] == "group_name"
    assert header[3] == "user_type"
    assert len(header) > 4 # 日付ヘッダーがあるはず (デフォルト90日分)
    
    # 作成したユーザーの行を探す
    user_row = next((row for row in rows[1:] if row[1] == user_id), None)
    assert user_row is not None
    assert user_row[0] == "Csv User All"
    assert user_row[2] == "CsvTestGroupAll"
    assert user_row[3] == "CsvTestUserTypeAll"
    # test_dateに対応する列にlocation名が入っているか確認
    try:
        date_col_index = header.index(date.today().strftime("%Y/%m/%d"))
        assert user_row[date_col_index] == "CsvTestLocation All"
    except ValueError:
        pytest.fail(f"Date header {date.today().strftime('%Y/%m/%d')} not found in CSV")

async def test_download_csv_success_month_sjis(async_client: AsyncClient) -> None:
    """月指定あり、SJISエンコーディングでCSVが正常にダウンロードされることをテストします。"""
    group_id = await create_test_group_via_api(async_client, "CsvTestGroupMonth")
    user_type_id = await create_test_user_type_via_api(async_client, "CsvTestUserTypeMonth")
    user_id = await create_test_user_via_api(async_client, "csv_user_month", "Csv User Month", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "CsvTestLocation Month")

    target_month = date.today().replace(day=1) # 今月1日
    test_date_in_month = target_month.isoformat()
    test_date_outside_month = (target_month - timedelta(days=1)).isoformat() # 先月末
    month_param = target_month.strftime("%Y-%m")

    await async_client.post("/api/attendances", data={"user_id": user_id, "date": test_date_in_month, "location_id": str(location_id)})
    await async_client.post("/api/attendances", data={"user_id": user_id, "date": test_date_outside_month, "location_id": str(location_id)})

    response = await async_client.get(f"/api/csv/download?month={month_param}&encoding=sjis")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/csv; charset=shift_jis"
    assert f"attachment; filename=\"work_entries_{month_param}.csv\"" in response.headers["content-disposition"]

    # SJISでデコードして検証
    try:
        csv_content = response.content.decode("shift_jis")
    except UnicodeDecodeError:
        pytest.fail("Failed to decode CSV content as Shift_JIS")
        
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) >= 2
    header = rows[0]
    # ヘッダーの日付が指定月のみであることを確認 (例: ヘッダー数をチェック)
    # 月の日数を取得
    _, days_in_month = calendar.monthrange(target_month.year, target_month.month)
    assert len(header) == 4 + days_in_month # 基本ヘッダー4 + 月の日数
    
    user_row = next((row for row in rows[1:] if row[1] == user_id), None)
    assert user_row is not None
    # test_date_in_month の列にデータがあり、outside の日付列がない(または空)ことを確認
    try:
        date_col_index = header.index(target_month.strftime("%Y/%m/%d"))
        assert user_row[date_col_index] == "CsvTestLocation Month"
    except ValueError:
         pytest.fail(f"Date header {target_month.strftime('%Y/%m/%d')} not found in CSV")
    # outside date がヘッダーに含まれていないことを確認
    assert (target_month - timedelta(days=1)).strftime("%Y/%m/%d") not in header

async def test_download_csv_no_data(async_client: AsyncClient) -> None:
    """データがない場合にヘッダー行のみのCSVが返されることをテストします。"""
    # データがないであろう未来の月を指定
    future_month = (date.today() + relativedelta(months=6)).strftime("%Y-%m")
    response = await async_client.get(f"/api/csv/download?month={future_month}")
    assert response.status_code == status.HTTP_200_OK
    csv_content = response.text
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1 # ヘッダー行のみ
    assert len(rows[0]) > 4 # ヘッダー列自体は存在する
    assert rows[0][0] == "user_name"

async def test_download_csv_invalid_month(async_client: AsyncClient) -> None:
    """無効な月形式でリクエストした場合に400エラーが返されることをテストします。"""
    response = await async_client.get("/api/csv/download?month=invalid-month")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "月の形式が無効です" in response.json()["detail"]

async def test_download_csv_invalid_encoding(async_client: AsyncClient) -> None:
    """無効なエンコーディングでリクエストした場合に400エラーが返されることをテストします。"""
    response = await async_client.get("/api/csv/download?encoding=invalid-encoding")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "無効なエンコーディングです" in response.json()["detail"] 