"""
社員種別APIのテスト

POST /api/user_types: 社員種別作成
GET /api/user_types: 社員種別一覧取得  
PUT /api/user_types/{user_type_id}: 社員種別更新
DELETE /api/user_types/{user_type_id}: 社員種別削除
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

# モデルとスキーマ、CRUD操作をインポート
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type
# User 関連のインポートを追加
from app.models.user import User
from app.schemas.user import UserCreate
from app.crud.user import user as crud_user
from app.models.group import Group # User は Group に依存
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group

pytestmark = pytest.mark.asyncio


# --- GET /api/user_types Tests ---

async def test_get_user_types_empty(async_client: AsyncClient) -> None:
    """
    GET /api/user_types - 社員種別が1つもない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get("/api/user_types")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "user_types" in data
    assert len(data["user_types"]) == 0


async def test_get_user_types_with_data(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    GET /api/user_types - 社員種別が存在する場合に正しくソートされたリストが返されることをテストします。
    """
    # テスト用データを作成
    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name=test_data_tracker['create_test_name']("Type_B")))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name=test_data_tracker['create_test_name']("Type_A")))
    
    # 作成したオブジェクトを追跡対象に登録
    test_data_tracker['register_created_object']('user_types', user_type1)
    test_data_tracker['register_created_object']('user_types', user_type2)
    
    db.commit()

    response = await async_client.get("/api/user_types")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "user_types" in data
    assert len(data["user_types"]) == 2

    # APIは名前順で返すはず
    assert data["user_types"][0]["name"] == user_type2.name  # Type_A が先
    assert data["user_types"][0]["id"] == user_type2.id
    assert data["user_types"][1]["name"] == user_type1.name  # Type_B が後
    assert data["user_types"][1]["id"] == user_type1.id


# --- POST /api/user_types Tests ---

async def test_create_user_type_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    POST /api/user_types - 社員種別が正常に作成されることをテストします。
    """
    user_type_name = test_data_tracker['create_test_name']("New_Type")
    payload = {"name": user_type_name}
    
    response = await async_client.post("/api/user_types", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == user_type_name
    assert "id" in data
    user_type_id = data["id"]

    # DBに実際に作成されたかを確認
    db_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert db_user_type is not None
    assert db_user_type.name == user_type_name
    
    # 作成したオブジェクトを追跡対象に登録
    test_data_tracker['register_created_object']('user_types', db_user_type)


async def test_create_user_type_missing_name(async_client: AsyncClient) -> None:
    """
    POST /api/user_types - 社員種別名がない場合に 400 エラーが返されることをテストします。
    """
    # ケース1: name が空文字列
    payload_empty = {"name": ""}
    response_empty = await async_client.post("/api/user_types", json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "社員種別名を入力してください"

    # ケース2: name フィールド自体がない
    payload_no_name: dict = {}
    response_no_name = await async_client.post("/api/user_types", json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_user_type_duplicate_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    POST /api/user_types - 重複する社員種別名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    user_type_name = test_data_tracker['create_test_name']("Duplicate_Type")
    # 最初に社員種別を作成しておく
    existing_user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name=user_type_name))
    test_data_tracker['register_created_object']('user_types', existing_user_type)
    db.commit()

    # 同じ名前で再度作成しようとする
    payload = {"name": user_type_name}
    response = await async_client.post("/api/user_types", json=payload)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "この社員種別名は既に存在します"


# --- PUT /api/user_types/{user_type_id} Tests ---

async def test_update_user_type_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/user_types/{user_type_id} - 社員種別が正常に更新されることをテストします。
    """
    # 更新対象の社員種別を作成
    original_name = test_data_tracker['create_test_name']("Original_Type")
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    test_data_tracker['register_created_object']('user_types', user_type_to_update)
    db.commit()
    user_type_id = user_type_to_update.id
    
    # 更新後の名前
    updated_name = test_data_tracker['create_test_name']("Updated_Type")
    payload = {"name": updated_name}
    
    response = await async_client.put(f"/api/user_types/{user_type_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == user_type_id

    # DBで実際に更新されたかを確認
    db.refresh(user_type_to_update)
    assert user_type_to_update.name == updated_name


async def test_update_user_type_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_type_id = 9999
    payload = {"name": "Non Existent Update"}
    
    response = await async_client.put(f"/api/user_types/{non_existent_user_type_id}", json=payload)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


async def test_update_user_type_duplicate_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/user_types/{user_type_id} - 他の社員種別が使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    # 2つの社員種別を作成
    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name=test_data_tracker['create_test_name']("Type_To_Update")))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name=test_data_tracker['create_test_name']("Existing_Other_Type")))
    
    test_data_tracker['register_created_object']('user_types', user_type1)
    test_data_tracker['register_created_object']('user_types', user_type2)
    db.commit()
    
    user_type_id_to_update = user_type1.id
    existing_name = user_type2.name

    # user_type1 の名前を user_type2 と同じにしようとする
    payload = {"name": existing_name}
    response = await async_client.put(f"/api/user_types/{user_type_id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]


async def test_update_user_type_same_name(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    PUT /api/user_types/{user_type_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    # 更新対象の社員種別を作成
    original_name = test_data_tracker['create_test_name']("Same_Name_Type")
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    test_data_tracker['register_created_object']('user_types', user_type_to_update)
    db.commit()
    user_type_id = user_type_to_update.id

    # 同じ名前で更新
    payload = {"name": original_name}
    response = await async_client.put(f"/api/user_types/{user_type_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == user_type_id

    # DB で名前が変わっていないことを確認
    db.refresh(user_type_to_update)
    assert user_type_to_update.name == original_name


# --- DELETE /api/user_types/{user_type_id} Tests ---

async def test_delete_user_type_success(async_client: AsyncClient, db: Session, test_data_tracker: dict) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 社員種別が正常に削除されることをテストします。
    """
    # 削除対象の社員種別を作成
    user_type_to_delete = crud_user_type.create(db, obj_in=UserTypeCreate(name=test_data_tracker['create_test_name']("Type_To_Delete")))
    test_data_tracker['register_created_object']('user_types', user_type_to_delete)
    db.commit()
    user_type_id = user_type_to_delete.id

    # 社員種別を削除
    response = await async_client.delete(f"/api/user_types/{user_type_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # DBから削除されたかを確認
    deleted_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert deleted_user_type is None
    
    # 削除されたので追跡対象からも除外
    test_data_tracker['created_objects']['user_types'].remove(user_type_to_delete)


async def test_delete_user_type_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_type_id = 9999
    
    response = await async_client.delete(f"/api/user_types/{non_existent_user_type_id}")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_delete_user_type_in_use(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/user_types/{user_type_id} - ユーザーに割り当てられている社員種別を削除しようとした場合にエラーが発生することをテストします。
    """
    # 依存関係の準備: Group
    group = crud_group.create(db, obj_in=GroupCreate(name="Test Group for UserType Delete"))
    db.commit()

    # 削除対象の社員種別を作成
    user_type_to_delete = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType In Use"))
    db.commit()
    user_type_id = user_type_to_delete.id

    # この社員種別を使用するユーザーを作成
    user_id_for_test = "testuser_utdel"
    crud_user.create(db, obj_in=UserCreate(id=user_id_for_test, username="Test User UTDel", group_id=group.id, user_type_id=user_type_id)) # type: ignore
    db.commit()

    # この社員種別を削除しようとする
    response = await async_client.delete(f"/api/user_types/{user_type_id}")

    # 使用中のため削除できないはず
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "この社員種別は1人のユーザーに割り当てられているため削除できません" in response.json()["detail"]

    # DBに残っていることを確認
    still_exists = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert still_exists is not None 