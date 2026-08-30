import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
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
    社員種別が登録されていない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get("/api/user_types")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"user_types": []}


async def test_get_user_types_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session) -> None:
    """
    社員種別が登録されている場合にリストが正しく返されることをテストします。
    """
    # テストデータの作成
    ut1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType B"))
    ut2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType A"))
    db.commit()

    response = await async_client.get("/api/user_types")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "user_types" in data
    assert len(data["user_types"]) == 2

    # APIは名前順で返すはず
    assert data["user_types"][0]["name"] == "UserType A"
    assert data["user_types"][0]["id"] == ut2.id
    assert data["user_types"][1]["name"] == "UserType B"
    assert data["user_types"][1]["id"] == ut1.id


# --- POST /api/user_types Tests ---

async def test_create_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/user_types - 社員種別が正常に作成されることをテストします。
    """
    user_type_name = "New Test UserType"
    payload = {"name": user_type_name}
    response = await async_client.post("/api/user_types", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == user_type_name
    assert "id" in data
    user_type_id = data["id"]

    db_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert db_user_type is not None
    assert db_user_type.name == user_type_name


async def test_create_user_type_missing_name(async_client: AsyncClient) -> None:
    """
    POST /api/user_types - 社員種別名がない場合にエラーが返されることをテストします。
    """
    payload_empty = {"name": ""}
    response_empty = await async_client.post("/api/user_types", json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "社員種別名を入力してください"

    payload_no_name: dict = {}
    response_no_name = await async_client.post("/api/user_types", json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_user_type_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/user_types - 重複する社員種別名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    user_type_name = "Duplicate UserType"
    # 最初に社員種別を作成しておく（API経由で）
    await async_client.post("/api/user_types", json={"name": user_type_name})
    # db.commit() # APIコール内でコミットされるはず

    # 同じ名前で再度作成しようとする
    payload = {"name": user_type_name}
    response = await async_client.post("/api/user_types", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # サービス層が返すエラーメッセージに合わせる
    assert response.json()["detail"] == "この社員種別名は既に存在します"


# --- PUT /api/user_types/{user_type_id} Tests ---

async def test_update_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 社員種別が正常に更新されることをテストします。
    """
    original_name = "Original UserType Name"
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    db.commit()
    user_type_id = user_type_to_update.id
    
    updated_name = "Updated UserType Name"
    payload = {"name": updated_name}
    response = await async_client.put(f"/api/user_types/{user_type_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == user_type_id

    db.refresh(user_type_to_update)
    assert user_type_to_update.name == updated_name


async def test_update_user_type_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_id = 9999
    payload = {"name": "Non Existent Update"}
    response = await async_client.put(f"/api/user_types/{non_existent_id}", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


async def test_update_user_type_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 他の社員種別が使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    ut1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType To Update"))
    ut2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Existing Other UserType"))
    db.commit()
    id_to_update = ut1.id
    existing_name = ut2.name

    payload = {"name": existing_name}
    response = await async_client.put(f"/api/user_types/{id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]


async def test_update_user_type_same_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    original_name = "Same Name UserType"
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    db.commit()
    user_type_id = user_type_to_update.id
    
    payload = {"name": original_name}
    response = await async_client.put(f"/api/user_types/{user_type_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == user_type_id

    db.refresh(user_type_to_update)
    assert user_type_to_update.name == original_name


# --- DELETE /api/user_types/{user_type_id} Tests ---

async def test_delete_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 社員種別が正常に削除されることをテストします。
    """
    user_type_to_delete = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType To Delete"))
    db.commit()
    user_type_id = user_type_to_delete.id

    response = await async_client.delete(f"/api/user_types/{user_type_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert deleted_user_type is None

async def test_delete_user_type_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_id = 9999
    response = await async_client.delete(f"/api/user_types/{non_existent_id}")
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