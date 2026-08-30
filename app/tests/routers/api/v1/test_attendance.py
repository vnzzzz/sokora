"""
勤怠APIエンドポイント (/api/attendances) のテスト
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import date, timedelta
import csv
import io

# ヘルパー関数や依存関係をインポート (必要に応じて)
# from tests.utils import create_test_user, create_test_location # 仮のutils関数

pytestmark = pytest.mark.asyncio

# --- Helper Functions ---

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


# --- POST /api/attendances Tests ---

async def test_create_attendance_success(async_client: AsyncClient) -> None:
    """
    正常に勤怠データが作成されることをテストします。
    作成後、GETエンドポイントでデータを確認します。
    """
    # 依存関係をAPI経由で作成
    group_id = await create_test_group_via_api(async_client, "AttTestGroup")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserType")
    user_id = await create_test_user_via_api(async_client, "att_user_success", "Att User Success", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation Success")
    
    test_date = date.today().isoformat()
    
    # FormDataとして送信
    payload = {
        "user_id": user_id,
        "date": test_date,
        "location_id": str(location_id) # FormDataでは通常文字列
    }
    
    response = await async_client.post("/api/attendances", data=payload)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 削除したエンドポイントを使わずに、get_attendancesを使ってデータを確認
    get_all_response = await async_client.get("/api/attendances")
    assert get_all_response.status_code == status.HTTP_200_OK
    
    all_attendances = get_all_response.json()["records"]
    found_attendance = None
    for att in all_attendances:
        if att["user_id"] == user_id and att["date"] == test_date:
            found_attendance = att
            break
    
    assert found_attendance is not None, "作成した勤怠データが見つかりません"
    assert found_attendance["location_id"] == location_id


async def test_create_attendance_duplicate(async_client: AsyncClient) -> None:
    """
    同じユーザーと日付で勤怠データを重複して作成しようとすると400エラーが発生することをテストします。
    """
    # 依存関係をAPI経由で作成
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDup")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDup")
    user_id = await create_test_user_via_api(async_client, "att_user_dup", "Att User Dup", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation Dup")

    test_date = (date.today() - timedelta(days=1)).isoformat() # 昨日日付を使用
    
    payload = {
        "user_id": user_id,
        "date": test_date,
        "location_id": str(location_id)
    }

    # 1回目の作成 (成功するはず)
    response1 = await async_client.post("/api/attendances", data=payload)
    assert response1.status_code == status.HTTP_204_NO_CONTENT

    # 2回目の作成 (失敗するはず)
    response2 = await async_client.post("/api/attendances", data=payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に勤怠データが存在します" in response2.json()["detail"]


async def test_create_attendance_invalid_user(async_client: AsyncClient) -> None:
    """
    存在しないユーザーIDで勤怠データを作成しようとすると404エラーが発生することをテストします。
    """
    location_id = await create_test_location_via_api(async_client, "AttTestLocation InvUser")
    test_date = date.today().isoformat()
    
    payload = {
        "user_id": "non_existent_user",
        "date": test_date,
        "location_id": str(location_id)
    }

    response = await async_client.post("/api/attendances", data=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "User with id non_existent_user not found" in response.json()["detail"] # エラーメッセージを確認


async def test_create_attendance_invalid_location(async_client: AsyncClient) -> None:
    """
    存在しない勤務場所IDで勤怠データを作成しようとすると404エラーが発生することをテストします。
    """
    group_id = await create_test_group_via_api(async_client, "AttTestGroupInvLoc")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeInvLoc")
    user_id = await create_test_user_via_api(async_client, "att_user_inv_loc", "Att User InvLoc", group_id, user_type_id)
    test_date = date.today().isoformat()
    non_existent_location_id = 99999

    payload = {
        "user_id": user_id,
        "date": test_date,
        "location_id": str(non_existent_location_id)
    }

    response = await async_client.post("/api/attendances", data=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Location with id {non_existent_location_id} not found" in response.json()["detail"] # エラーメッセージを確認


async def test_create_attendance_invalid_date_format(async_client: AsyncClient) -> None:
    """
    無効な日付形式で勤怠データを作成しようとすると422エラーが発生することをテストします。
    """
    group_id = await create_test_group_via_api(async_client, "AttTestGroupInvDate")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeInvDate")
    user_id = await create_test_user_via_api(async_client, "att_user_inv_date", "Att User InvDate", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation InvDate")
    invalid_date_str = "2023-13-01" # 無効な日付

    payload = {
        "user_id": user_id,
        "date": invalid_date_str,
        "location_id": str(location_id)
    }

    response = await async_client.post("/api/attendances", data=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "日付の形式が無効です" in response.json()["detail"] # エラーメッセージを確認

# --- GET /api/attendances/day/{day} Tests ---

async def test_get_day_attendance_success(async_client: AsyncClient) -> None:
    """特定の日の全ユーザーの勤怠データを正常に取得できることをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDay")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDay")
    user1_id = await create_test_user_via_api(async_client, "att_user_day1", "Att User Day 1", group_id, user_type_id)
    user2_id = await create_test_user_via_api(async_client, "att_user_day2", "Att User Day 2", group_id, user_type_id)
    location1_id = await create_test_location_via_api(async_client, "AttTestLocation Day1")
    location2_id = await create_test_location_via_api(async_client, "AttTestLocation Day2")

    test_day = date.today().isoformat()
    other_day = (date.today() - timedelta(days=1)).isoformat()

    # データ作成 (test_dayに2件、other_dayに1件)
    await async_client.post("/api/attendances", data={"user_id": user1_id, "date": test_day, "location_id": str(location1_id)})
    await async_client.post("/api/attendances", data={"user_id": user2_id, "date": test_day, "location_id": str(location2_id)})
    await async_client.post("/api/attendances", data={"user_id": user1_id, "date": other_day, "location_id": str(location1_id)})

    response = await async_client.get(f"/api/attendances/day/{test_day}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) > 0 # データが存在することを確認
    # レスポンス形式が {location_name: [...]} になっていることを想定
    day_data_values = list(data["data"].values()) # 場所ごとのリストを取得
    all_entries = [entry for sublist in day_data_values for entry in sublist] # 全エントリをフラット化
    assert len(all_entries) == 2 # test_dayには2件のレコード
    found_users = {entry["user_id"] for entry in all_entries}
    assert user1_id in found_users
    assert user2_id in found_users

async def test_get_day_attendance_no_records(async_client: AsyncClient) -> None:
    """記録がない日にGETすると空のデータが返されることをテストします。"""
    test_day = (date.today() + timedelta(days=10)).isoformat() # 未来の日付など、記録がないであろう日付
    response = await async_client.get(f"/api/attendances/day/{test_day}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["data"] == {}


# --- PUT /api/attendances/{attendance_id} Tests ---

async def test_update_attendance_success(async_client: AsyncClient) -> None:
    """勤怠データを正常に更新できることをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupPut")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypePut")
    user_id = await create_test_user_via_api(async_client, "att_user_put", "Att User Put", group_id, user_type_id)
    location1_id = await create_test_location_via_api(async_client, "AttTestLocation Put1")
    location2_id = await create_test_location_via_api(async_client, "AttTestLocation Put2")

    test_date = date.today().isoformat()

    # 初期データ作成
    create_payload = {"user_id": user_id, "date": test_date, "location_id": str(location1_id)}
    create_response = await async_client.post("/api/attendances", data=create_payload)
    assert create_response.status_code == status.HTTP_204_NO_CONTENT

    # 初期データ作成後にIDを取得する必要がある
    get_all_response = await async_client.get("/api/attendances")
    assert get_all_response.status_code == status.HTTP_200_OK
    all_attendances = get_all_response.json()["records"]
    found_attendance = None
    for att in all_attendances:
        if att["user_id"] == user_id and att["date"] == test_date:
            found_attendance = att
            break
    assert found_attendance is not None, "作成した勤怠データが見つかりません"
    attendance_id = found_attendance["id"]

    # 更新ペイロード (JSON)
    update_payload = {"location_id": location2_id}
    response = await async_client.put(f"/api/attendances/{attendance_id}", json=update_payload)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 更新後のデータを確認
    get_updated_response = await async_client.get("/api/attendances")
    updated_attendances = get_updated_response.json()["records"]
    updated_attendance = None
    for att in updated_attendances:
        if att["id"] == attendance_id:
            updated_attendance = att
            break
    assert updated_attendance is not None, "更新した勤怠データが見つかりません"
    assert updated_attendance["location_id"] == location2_id # 更新後の location_id を確認

async def test_update_attendance_not_found(async_client: AsyncClient) -> None:
    """存在しない勤怠IDでPUTすると404エラーが発生することをテストします。"""
    non_existent_attendance_id = 99999
    location_id = await create_test_location_via_api(async_client, "AttTestLocation PutNF")
    update_payload = {"location_id": location_id}
    response = await async_client.put(f"/api/attendances/{non_existent_attendance_id}", json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Attendance with id {non_existent_attendance_id} not found" in response.json()["detail"]

async def test_update_attendance_invalid_location(async_client: AsyncClient) -> None:
    """更新時に存在しない勤務場所IDを指定すると404エラーが発生することをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupPutInvLoc")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypePutInvLoc")
    user_id = await create_test_user_via_api(async_client, "att_user_put_invloc", "Att User Put InvLoc", group_id, user_type_id)
    location1_id = await create_test_location_via_api(async_client, "AttTestLocation PutInvLoc1")
    non_existent_location_id = 99998

    test_date = date.today().isoformat()

    # 初期データ作成
    create_payload = {"user_id": user_id, "date": test_date, "location_id": str(location1_id)}
    create_response = await async_client.post("/api/attendances", data=create_payload)
    assert create_response.status_code == status.HTTP_204_NO_CONTENT

    # ID取得
    get_all_response = await async_client.get("/api/attendances")
    all_attendances = get_all_response.json()["records"]
    found_attendance = None
    for att in all_attendances:
        if att["user_id"] == user_id and att["date"] == test_date:
            found_attendance = att
            break
    assert found_attendance is not None, "作成した勤怠データが見つかりません"
    attendance_id = found_attendance["id"]

    # 更新ペイロード (JSON)
    update_payload = {"location_id": non_existent_location_id}
    response = await async_client.put(f"/api/attendances/{attendance_id}", json=update_payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Location with id {non_existent_location_id} not found" in response.json()["detail"]


# --- DELETE /api/attendances/{attendance_id} Tests ---

async def test_delete_attendance_success(async_client: AsyncClient) -> None:
    """勤怠データをID指定で正常に削除できることをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDel")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDel")
    user_id = await create_test_user_via_api(async_client, "att_user_del", "Att User Del", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation Del")

    test_date = date.today().isoformat()

    # データ作成
    create_payload = {"user_id": user_id, "date": test_date, "location_id": str(location_id)}
    create_response = await async_client.post("/api/attendances", data=create_payload)
    assert create_response.status_code == status.HTTP_204_NO_CONTENT

    # ID取得
    get_all_response = await async_client.get("/api/attendances")
    all_attendances = get_all_response.json()["records"]
    found_attendance = None
    for att in all_attendances:
        if att["user_id"] == user_id and att["date"] == test_date:
            found_attendance = att
            break
    assert found_attendance is not None, "作成した勤怠データが見つかりません"
    attendance_id = found_attendance["id"]

    # 削除リクエスト
    response = await async_client.delete(f"/api/attendances/{attendance_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # GET エンドポイントでデータが削除されたことを確認
    get_all_response = await async_client.get("/api/attendances")
    updated_attendances = get_all_response.json()["records"]
    updated_attendance = None
    for att in updated_attendances:
        if att["id"] == attendance_id:
            updated_attendance = att
            break
    assert updated_attendance is None, "削除した勤怠データが見つかります"

async def test_delete_attendance_not_found(async_client: AsyncClient) -> None:
    """存在しない勤怠IDでDELETEすると404エラーが発生することをテストします。"""
    non_existent_attendance_id = 99997
    response = await async_client.delete(f"/api/attendances/{non_existent_attendance_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND # ルーター側のget_or_404が先に機能する
    assert f"Attendance with id {non_existent_attendance_id} not found" in response.json()["detail"]


# --- DELETE /api/attendances?user_id={user_id}&date={date} Tests ---

async def test_delete_attendance_by_user_date_success(async_client: AsyncClient) -> None:
    """ユーザーIDと日付指定で勤怠データを正常に削除できることをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDelUD")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDelUD")
    user_id = await create_test_user_via_api(async_client, "att_user_del_ud", "Att User Del UD", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation DelUD")

    test_date = date.today().isoformat()

    # データ作成
    create_payload = {"user_id": user_id, "date": test_date, "location_id": str(location_id)}
    create_response = await async_client.post("/api/attendances", data=create_payload)
    assert create_response.status_code == status.HTTP_204_NO_CONTENT

    # 削除リクエスト
    response = await async_client.delete(f"/api/attendances?user_id={user_id}&date={test_date}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # 削除したエンドポイントを使わずに、get_attendancesを使ってデータを確認
    get_all_response = await async_client.get("/api/attendances")
    assert get_all_response.status_code == status.HTTP_200_OK
    
    all_attendances = get_all_response.json()["records"]
    found_attendance = None
    for att in all_attendances:
        if att["user_id"] == user_id and att["date"] == test_date:
            found_attendance = att
            break
    
    assert found_attendance is None, "削除したはずの勤怠データが見つかります"

async def test_delete_attendance_by_user_date_user_not_found(async_client: AsyncClient) -> None:
    """存在しないユーザーIDでDELETEすると404エラーが発生することをテストします。"""
    non_existent_user_id = "no_such_del_user"
    test_date = date.today().isoformat()
    response = await async_client.delete(f"/api/attendances?user_id={non_existent_user_id}&date={test_date}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"ユーザー '{non_existent_user_id}' の日付" in response.json()["detail"]
    assert "勤怠データが見つかりません" in response.json()["detail"]

async def test_delete_attendance_by_user_date_record_not_found(async_client: AsyncClient) -> None:
    """削除対象のレコードが存在しない場合でも404エラーが発生することを確認します。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDelUDNF")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDelUDNF")
    user_id = await create_test_user_via_api(async_client, "att_user_del_ud_nf", "Att User Del UD NF", group_id, user_type_id)
    test_date = (date.today() - timedelta(days=5)).isoformat() # 記録がない日付

    response = await async_client.delete(f"/api/attendances?user_id={user_id}&date={test_date}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"ユーザー '{user_id}' の日付" in response.json()["detail"]
    assert "勤怠データが見つかりません" in response.json()["detail"]

async def test_delete_attendance_by_user_date_invalid_date(async_client: AsyncClient) -> None:
    """無効な日付形式でDELETEすると422エラーが発生することをテストします。"""
    group_id = await create_test_group_via_api(async_client, "AttTestGroupDelUDID")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeDelUDID")
    user_id = await create_test_user_via_api(async_client, "att_user_del_ud_id", "Att User Del UD ID", group_id, user_type_id)
    invalid_date = "invalid-date-format"

    response = await async_client.delete(f"/api/attendances?user_id={user_id}&date={invalid_date}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # ステータスコードの確認のみで十分


# --- GET /api/csv/download Tests ---

# async def test_download_csv_success_all(async_client: AsyncClient) -> None:
#    ... (削除) ...

# async def test_download_csv_success_month_sjis(async_client: AsyncClient) -> None:
#    ... (削除) ...

# async def test_download_csv_no_data(async_client: AsyncClient) -> None:
#    ... (削除) ...

# async def test_download_csv_invalid_month(async_client: AsyncClient) -> None:
#    ... (削除) ...

# async def test_download_csv_invalid_encoding(async_client: AsyncClient) -> None:
#    ... (削除) ...

# 削除対象の最後のテストの後ろに不要なコメントが残っている場合も削除
# --- 他のHTTPメソッド (GET, PUT, DELETE) のテストも同様に追加 ---
# 例:
# ...

# ... (他の DELETE テスト) ...

# ... (他の GET テスト) ...

# ... (他の PUT テスト) ...

# ... (他の DELETE テスト) ... 