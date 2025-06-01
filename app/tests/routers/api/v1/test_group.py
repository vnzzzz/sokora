"""
グループAPIのテスト

POST /api/groups: グループ作成
GET /api/groups: グループ一覧取得  
PUT /api/groups/{group_id}: グループ更新
DELETE /api/groups/{group_id}: グループ削除
"""

import pytest
from fastapi import status, FastAPI
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.group import Group
from app.schemas.group import GroupCreate


async def test_get_groups_empty(async_client: AsyncClient) -> None:
    """
    GET /api/groups - グループが1つもない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get("/api/groups")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "groups" in data
    assert len(data["groups"]) == 0


async def test_get_groups_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session, test_data_tracker: dict) -> None:
    """
    GET /api/groups - グループが存在する場合に正しくソートされたリストが返されることをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group
    
    # テスト用データを作成
    group1 = crud_group.create(db, obj_in=GroupCreate(name=test_data_tracker['create_test_name']("Group_B")))
    group2 = crud_group.create(db, obj_in=GroupCreate(name=test_data_tracker['create_test_name']("Group_A")))
    
    # 作成したオブジェクトを追跡対象に登録
    test_data_tracker['register_created_object']('groups', group1)
    test_data_tracker['register_created_object']('groups', group2)
    
    db.commit()

    response = await async_client.get("/api/groups")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "groups" in data
    assert len(data["groups"]) == 2

    # APIは名前順で返すはず
    assert data["groups"][0]["name"] == group2.name  # Group_A が先
    assert data["groups"][0]["id"] == group2.id
    assert data["groups"][1]["name"] == group1.name  # Group_B が後
    assert data["groups"][1]["id"] == group1.id


async def test_create_group_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    POST /api/groups - グループが正常に作成されることをテストします。
    """
    group_name = test_data_tracker['create_test_name']("New_Group")
    payload = {"name": group_name}
    
    response = await async_client.post("/api/groups", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == group_name
    assert "id" in data
    group_id = data["id"]

    # DBに実際に作成されたかを確認
    db_group = db.query(Group).filter(Group.id == group_id).first()
    assert db_group is not None
    assert db_group.name == group_name
    
    # 作成したオブジェクトを追跡対象に登録
    test_data_tracker['register_created_object']('groups', db_group)


async def test_create_group_missing_name(async_client: AsyncClient) -> None:
    """
    POST /api/groups - グループ名がない場合に 400 エラーが返されることをテストします。
    """
    # ケース1: name が空文字列
    payload_empty = {"name": ""}
    response_empty = await async_client.post("/api/groups", json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "グループ名を入力してください"

    # ケース2: name フィールド自体がない (不正なスキーマ)
    # FastAPI/Pydantic が 422 Unprocessable Entity を返すはず
    payload_no_name: dict = {}
    response_no_name = await async_client.post("/api/groups", json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_group_duplicate_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    POST /api/groups - 重複するグループ名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group
    
    group_name = test_data_tracker['create_test_name']("Duplicate_Group")
    # 最初にグループを作成しておく
    existing_group = crud_group.create(db, obj_in=GroupCreate(name=group_name))
    test_data_tracker['register_created_object']('groups', existing_group)
    db.commit()

    # 同じ名前で再度作成しようとする
    payload = {"name": group_name}
    response = await async_client.post("/api/groups", json=payload)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "このグループ名は既に存在します"


async def test_update_group_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/groups/{group_id} - グループが正常に更新されることをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group
    
    # 更新対象のグループを作成
    original_name = test_data_tracker['create_test_name']("Original_Group")
    group_to_update = crud_group.create(db, obj_in=GroupCreate(name=original_name))
    test_data_tracker['register_created_object']('groups', group_to_update)
    db.commit()
    group_id = group_to_update.id
    
    # 更新後の名前
    updated_name = test_data_tracker['create_test_name']("Updated_Group")
    payload = {"name": updated_name}
    
    response = await async_client.put(f"/api/groups/{group_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == group_id

    # DBで実際に更新されたかを確認
    db.refresh(group_to_update) # オブジェクトの状態を最新化
    assert group_to_update.name == updated_name


async def test_update_group_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/groups/{group_id} - 存在しないグループIDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_group_id = 9999
    payload = {"name": "Non Existent Update"}
    
    response = await async_client.put(f"/api/groups/{non_existent_group_id}", json=payload)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


async def test_update_group_duplicate_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/groups/{group_id} - 他のグループが使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group

    # 2つのグループを作成
    group1 = crud_group.create(db, obj_in=GroupCreate(name=test_data_tracker['create_test_name']("Group_To_Update")))
    group2 = crud_group.create(db, obj_in=GroupCreate(name=test_data_tracker['create_test_name']("Existing_Other_Group")))
    
    test_data_tracker['register_created_object']('groups', group1)
    test_data_tracker['register_created_object']('groups', group2)
    db.commit()
    
    group_id_to_update = group1.id
    existing_name = group2.name

    # group1 の名前を group2 と同じにしようとする
    payload = {"name": existing_name}
    response = await async_client.put(f"/api/groups/{group_id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]


async def test_update_group_same_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/groups/{group_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group

    # 更新対象のグループを作成
    original_name = test_data_tracker['create_test_name']("Same_Name_Group")
    group_to_update = crud_group.create(db, obj_in=GroupCreate(name=original_name))
    test_data_tracker['register_created_object']('groups', group_to_update)
    db.commit()
    group_id = group_to_update.id
    
    # 同じ名前で更新
    payload = {"name": original_name}
    response = await async_client.put(f"/api/groups/{group_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == group_id

    # DB で名前が変わっていないことを確認
    db.refresh(group_to_update)
    assert group_to_update.name == original_name


async def test_delete_group_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    DELETE /api/groups/{group_id} - グループが正常に削除されることをテストします。
    """
    # 関数内で crud_group をインポート
    from app.crud.group import group as crud_group

    # 削除対象のグループを作成
    group_to_delete = crud_group.create(db, obj_in=GroupCreate(name=test_data_tracker['create_test_name']("Group_To_Delete")))
    test_data_tracker['register_created_object']('groups', group_to_delete)
    db.commit()
    group_id = group_to_delete.id

    # グループを削除
    response = await async_client.delete(f"/api/groups/{group_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # DBから削除されたかを確認
    deleted_group = db.query(Group).filter(Group.id == group_id).first()
    assert deleted_group is None
    
    # 削除されたので追跡対象からも除外
    test_data_tracker['created_objects']['groups'].remove(group_to_delete)


async def test_delete_group_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/groups/{group_id} - 存在しないグループIDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_group_id = 9999
    
    response = await async_client.delete(f"/api/groups/{non_existent_group_id}")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"] 