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
    """月指定なしでCSVが正常にダウンロードされ、グループ・社員種別でソートされることをテストします (UTF-8)。"""
    # データ準備 (複数のユーザーを追加)
    group1_id = await create_test_group_via_api(async_client, "Group A")
    group2_id = await create_test_group_via_api(async_client, "Group B")
    type1_id = await create_test_user_type_via_api(async_client, "Type X")
    type2_id = await create_test_user_type_via_api(async_client, "Type Y")

    # ソート順を考慮したユーザー作成
    # 1. Group A, Type X
    await create_test_user_via_api(async_client, "user_ax", "User AX", group1_id, type1_id)
    # 2. Group A, Type Y
    await create_test_user_via_api(async_client, "user_ay", "User AY", group1_id, type2_id)
    # 3. Group B, Type X
    await create_test_user_via_api(async_client, "user_bx", "User BX", group2_id, type1_id)
    # 4. Group B, Type Y
    await create_test_user_via_api(async_client, "user_by", "User BY", group2_id, type2_id)
    # 5. Group B, Type Y (同名種別・グループの別ユーザー)
    await create_test_user_via_api(async_client, "user_by2", "User BY2", group2_id, type2_id)

    # (オプション) 適当な勤怠データも作成 (ソートの検証には直接関係ないが念のため)
    location_id = await create_test_location_via_api(async_client, "Default Location")
    test_date = date.today().isoformat()
    await async_client.post("/api/attendances", data={"user_id": "user_ax", "date": test_date, "location_id": str(location_id)})

    response = await async_client.get("/api/csv/download")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=\"work_entries.csv\"" in response.headers["content-disposition"]

    # CSV内容の検証
    csv_content = response.text
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    # 少なくともヘッダー + 作成した5ユーザーが存在することを確認
    # 他のテストで作成されたユーザーが含まれる可能性があるため >= とする
    assert len(rows) >= 6

    header = rows[0]
    assert header[0] == "user_name"
    assert header[1] == "user_id"
    assert header[2] == "group_name"
    assert header[3] == "user_type"

    # データ行のソート順を検証 (Group A -> Group B, その中で Type X -> Type Y)
    data_rows = rows[1:]
    # ユーザーIDを取得して期待される順序と比較
    user_ids = [row[1] for row in data_rows]
    expected_user_id_order = ["user_ax", "user_ay", "user_bx", "user_by", "user_by2"]

    # テスト中に他のユーザーが作成されている可能性を考慮し、
    # 作成したユーザーが期待する順序で *含まれていること* を検証する
    actual_order_indices = {uid: idx for idx, uid in enumerate(user_ids) if uid in expected_user_id_order}

    # 期待するユーザーがすべて存在するか確認
    for expected_id in expected_user_id_order:
        assert expected_id in actual_order_indices, f"Expected user ID {expected_id} not found in CSV rows: {user_ids}"

    # 期待する順序になっているか確認
    for i in range(len(expected_user_id_order) - 1):
        id1 = expected_user_id_order[i]
        id2 = expected_user_id_order[i+1]
        # 存在しないIDのエラーは上でキャッチされるはずなので、ここでは単純比較
        assert actual_order_indices[id1] < actual_order_indices[id2], (
            f"CSV order is incorrect: {id1} (index {actual_order_indices[id1]}) "
            f"should come before {id2} (index {actual_order_indices[id2]}) in {user_ids}"
        )

    # (オプション) 個々のユーザーデータの簡単な検証 (例: 最初のユーザー)
    first_data_row = next((row for row in data_rows if row[1] == "user_ax"), None)
    assert first_data_row is not None
    assert first_data_row[0] == "User AX"
    assert first_data_row[2] == "Group A"
    assert first_data_row[3] == "Type X"

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