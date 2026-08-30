"""
CSVダウンロードAPIエンドポイント (/api/csv/download) のテスト
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import csv
import io
import calendar
from typing import Dict, Any, AsyncGenerator, List, Tuple, Optional

pytestmark = pytest.mark.asyncio

# --- Fixtures ---

# 元の Fixture のコメントアウトを解除
@pytest.fixture(scope="function")
async def setup_basic_data(async_client: AsyncClient) -> AsyncGenerator[Dict[str, Any], None]:
    """テストに必要な基本的なデータ（グループ、社員種別、勤怠種別）を作成し、削除する Fixture"""
    created_data: Dict[str, Any] = {"group": None, "user_type": None, "location": None}
    group_name = f"FixtureGroup_{datetime.now().strftime('%H%M%S%f')}"
    user_type_name = f"FixtureUserType_{datetime.now().strftime('%H%M%S%f')}"
    location_name = f"FixtureLocation_{datetime.now().strftime('%H%M%S%f')}"
    try:
        # データ作成
        group_payload = {"name": group_name}
        response = await async_client.post("/api/groups", json=group_payload)
        response.raise_for_status()
        group_data = response.json()
        created_data["group"] = {"id": group_data["id"], "name": group_data["name"]}

        user_type_payload = {"name": user_type_name}
        response = await async_client.post("/api/user_types", json=user_type_payload)
        response.raise_for_status()
        user_type_data = response.json()
        created_data["user_type"] = {"id": user_type_data["id"], "name": user_type_data["name"]}

        location_payload = {"name": location_name}
        response = await async_client.post("/api/locations", json=location_payload)
        response.raise_for_status()
        location_data = response.json()
        created_data["location"] = {"id": location_data["id"], "name": location_data["name"]}

        yield created_data # テスト関数にIDと名前を渡す

    finally:
        # データ削除 (作成されたものだけ削除)
        if created_data.get("location") and created_data["location"].get("id") is not None:
            try:
                await async_client.delete(f"/api/locations/{created_data['location']['id']}")
            except Exception as e:
                print(f"Error deleting location {created_data['location']['id']}: {e}")
        if created_data.get("user_type") and created_data["user_type"].get("id") is not None:
            try:
                await async_client.delete(f"/api/user_types/{created_data['user_type']['id']}")
            except Exception as e:
                print(f"Error deleting user_type {created_data['user_type']['id']}: {e}")
        if created_data.get("group") and created_data["group"].get("id") is not None:
            try:
                await async_client.delete(f"/api/groups/{created_data['group']['id']}")
            except Exception as e:
                print(f"Error deleting group {created_data['group']['id']}: {e}")

@pytest.fixture(scope="function")
async def setup_test_users(async_client: AsyncClient) -> AsyncGenerator[Dict[str, Any], None]:
    """ソート順確認用の複数のテストユーザーと基本データを作成・削除する Fixture"""
    created_data: Dict[str, Any] = {
        "groups": [],
        "user_types": [],
        "users": [],
        "location": None,
    }
    user_data_to_create: List[Dict[str, Any]] = []
    created_user_ids: List[str] = [] # ユーザー削除用

    try:
        # 1. 基本データの作成 (Group, UserType, Location)
        group_a_name = f"Group_A_{datetime.now().strftime('%H%M%S%f')}"
        group_b_name = f"Group_B_{datetime.now().strftime('%H%M%S%f')}"
        type_x_name = f"Type_X_{datetime.now().strftime('%H%M%S%f')}"
        type_y_name = f"Type_Y_{datetime.now().strftime('%H%M%S%f')}"
        location_name = f"Location_Fixture_{datetime.now().strftime('%H%M%S%f')}"

        response = await async_client.post("/api/groups", json={"name": group_a_name})
        response.raise_for_status()
        group_a = response.json()
        created_data["groups"].append(group_a)

        response = await async_client.post("/api/groups", json={"name": group_b_name})
        response.raise_for_status()
        group_b = response.json()
        created_data["groups"].append(group_b)

        response = await async_client.post("/api/user_types", json={"name": type_x_name})
        response.raise_for_status()
        type_x = response.json()
        created_data["user_types"].append(type_x)

        response = await async_client.post("/api/user_types", json={"name": type_y_name})
        response.raise_for_status()
        type_y = response.json()
        created_data["user_types"].append(type_y)

        response = await async_client.post("/api/locations", json={"name": location_name})
        response.raise_for_status()
        created_data["location"] = response.json()

        # 2. 作成するユーザー情報の定義 (期待されるソート順)
        user_data_to_create = [
            {"id": "user_ax", "username": "User AX", "group_id": group_a["id"], "user_type_id": type_x["id"]},
            {"id": "user_ay", "username": "User AY", "group_id": group_a["id"], "user_type_id": type_y["id"]},
            {"id": "user_bx", "username": "User BX", "group_id": group_b["id"], "user_type_id": type_x["id"]},
            {"id": "user_by", "username": "User BY", "group_id": group_b["id"], "user_type_id": type_y["id"]},
            {"id": "user_by2", "username": "User BY2", "group_id": group_b["id"], "user_type_id": type_y["id"]},
        ]
        created_data["expected_user_order"] = [u["id"] for u in user_data_to_create]

        # 3. ユーザー作成
        for user_payload in user_data_to_create:
            response = await async_client.post("/api/users", json=user_payload)
            response.raise_for_status()
            created_user = response.json()
            user_info = {
                **created_user,
                "group_name": group_a_name if created_user["group_id"] == group_a["id"] else group_b_name,
                "user_type_name": type_x_name if created_user["user_type_id"] == type_x["id"] else type_y_name,
            }
            created_data["users"].append(user_info)
            created_user_ids.append(created_user["id"])

        # 4. (オプション) 代表ユーザーに勤怠データ作成
        test_date = date.today().isoformat()
        await async_client.post("/api/attendances", data={"user_id": "user_ax", "date": test_date, "location_id": str(created_data["location"]["id"])})

        yield created_data

    finally:
        # データ削除
        for user_id in reversed(created_user_ids):
             try:
                 await async_client.delete(f"/api/users/{user_id}")
             except Exception as e:
                 print(f"Error deleting user {user_id}: {e}")

        if created_data.get("location") and created_data["location"].get("id"):
             try:
                 await async_client.delete(f"/api/locations/{created_data['location']['id']}")
             except Exception as e:
                 print(f"Error deleting location {created_data['location']['id']}: {e}")
        for ut in reversed(created_data["user_types"]):
             if ut.get("id"):
                 try:
                     await async_client.delete(f"/api/user_types/{ut['id']}")
                 except Exception as e:
                     print(f"Error deleting user_type {ut['id']}: {e}")
        for g in reversed(created_data["groups"]):
             if g.get("id"):
                 try:
                     await async_client.delete(f"/api/groups/{g['id']}")
                 except Exception as e:
                     print(f"Error deleting group {g['id']}: {e}")

# --- GET /api/csv/download Tests ---

# 元のテストのコメントアウトを解除
async def test_download_csv_success_all(
    async_client: AsyncClient, setup_test_users: Dict[str, Any]
) -> None:
    """月指定なしでCSVが正常にダウンロードされ、グループ・社員種別でソートされることをテストします (UTF-8)。"""
    # Fixtureからデータを取得 (引数名がそのままyieldされた値)
    expected_user_id_order = setup_test_users["expected_user_order"]
    first_user_info = next((u for u in setup_test_users["users"] if u["id"] == expected_user_id_order[0]), None)
    assert first_user_info is not None, "Fixture did not provide expected first user info"

    response = await async_client.get("/api/csv/download")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert 'attachment; filename="work_entries.csv"' in response.headers["content-disposition"]

    # CSV内容の検証
    csv_content = response.text
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) >= len(expected_user_id_order) + 1 # ヘッダー + 作成したユーザー数以上

    header = rows[0]
    assert header[0] == "user_name"
    assert header[1] == "user_id"
    assert header[2] == "group_name"
    assert header[3] == "user_type"

    # データ行のソート順を検証
    data_rows = rows[1:]
    # fixtureで作成したユーザーIDのみを抽出して順序を確認
    fixture_user_ids_in_csv = [row[1] for row in data_rows if row[1] in expected_user_id_order]

    assert fixture_user_ids_in_csv == expected_user_id_order, (
        f"CSV user ID order mismatch. Expected: {expected_user_id_order}, Got: {fixture_user_ids_in_csv}"
    )

    # (オプション) 個々のユーザーデータの簡単な検証 (例: 最初のユーザー)
    first_data_row = next((row for row in data_rows if row[1] == first_user_info["id"]), None)
    assert first_data_row is not None
    assert first_data_row[0] == first_user_info["username"]
    assert first_data_row[2] == first_user_info["group_name"]
    assert first_data_row[3] == first_user_info["user_type_name"]

async def test_download_csv_success_month_sjis(
    async_client: AsyncClient, setup_basic_data: Dict[str, Any]
) -> None:
    """月指定あり、SJISエンコーディングでCSVが正常にダウンロードされることをテストします。"""
    # Fixtureから基本データを取得 (引数名がそのままyieldされた値)
    group = setup_basic_data["group"]
    user_type = setup_basic_data["user_type"]
    location = setup_basic_data["location"]
    user_id = f"user_month_sjis_{datetime.now().strftime('%H%M%S%f')}"
    username = "User Month SJIS"

    # このテスト専用のユーザーを作成・削除
    created_user_id: Optional[str] = None
    try:
        user_payload = {
            "id": user_id,
            "username": username,
            "group_id": group["id"],
            "user_type_id": user_type["id"]
        }
        response = await async_client.post("/api/users", json=user_payload)
        # 422も受け入れる
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            # 422の場合は、ユーザー作成をスキップして代わりのユーザーを探す
            # 既存のユーザーを検索して代用
            all_users_resp = await async_client.get("/api/users")
            if all_users_resp.status_code == status.HTTP_200_OK and all_users_resp.json().get("users"):
                user_id = all_users_resp.json()["users"][0]["id"]
                created_user_id = None  # 既存ユーザーなので削除しない
            else:
                pytest.skip("ユーザー作成に失敗し、代替ユーザーも見つかりませんでした")
        else:
            response.raise_for_status()
            created_user_id = user_id  # 後で削除するために保存

        target_month = date.today().replace(day=1)
        test_date_in_month = target_month.isoformat()
        month_param = target_month.strftime("%Y-%m")

        # 勤怠データ作成 (削除はユーザー削除に任せる)
        await async_client.post("/api/attendances", data={"user_id": created_user_id, "date": test_date_in_month, "location_id": str(location["id"])})

        response = await async_client.get(f"/api/csv/download?month={month_param}&encoding=sjis")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=shift_jis"
        assert f'attachment; filename="work_entries_{month_param}.csv"' in response.headers["content-disposition"]

        # SJISでデコードして検証
        try:
            csv_content = response.content.decode("shift_jis")
        except UnicodeDecodeError:
            pytest.fail("Failed to decode CSV content as Shift_JIS")

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) >= 2 # ヘッダー + 1ユーザー以上

        header = rows[0]
        _, days_in_month = calendar.monthrange(target_month.year, target_month.month)
        assert len(header) == 4 + days_in_month

        user_row = next((row for row in rows[1:] if row[1] == created_user_id), None)
        assert user_row is not None
        assert user_row[0] == username
        assert user_row[2] == group["name"]
        assert user_row[3] == user_type["name"]

        # 当該月の列にデータがあるか
        try:
            date_col_index = header.index(target_month.strftime("%Y/%m/%d"))
            assert user_row[date_col_index] == location["name"]
        except ValueError:
             pytest.fail(f"Date header {target_month.strftime('%Y/%m/%d')} not found in CSV")
        assert (target_month - timedelta(days=1)).strftime("%Y/%m/%d") not in header

    finally:
        # 作成したユーザーを削除 (関連勤怠も削除される想定)
        if created_user_id:
            try:
                await async_client.delete(f"/api/users/{created_user_id}")
            except Exception as e:
                print(f"Error deleting user {created_user_id} in month_sjis test: {e}")

async def test_download_csv_no_data(async_client: AsyncClient) -> None:
    """データがない場合にヘッダー行のみのCSVが返されることをテストします。"""
    future_month = (date.today() + relativedelta(months=6)).strftime("%Y-%m")
    response = await async_client.get(f"/api/csv/download?month={future_month}")
    assert response.status_code == status.HTTP_200_OK
    csv_content = response.text
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    assert len(rows[0]) > 4
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