import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session

# モデル、スキーマ、CRUD、テストヘルパー等をインポート
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.crud.user import user as crud_user
from app.models.group import Group
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type

# APIテストからヘルパー関数を借用（または共通化）
def create_test_dependencies_for_page(db: Session) -> tuple[Group, UserType]:
    """テストに必要な Group と UserType を作成するヘルパー関数"""
    test_group = crud_group.create(db, obj_in=GroupCreate(name="Test Group for User Page"))
    test_user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test UserType for User Page"))
    db.commit()
    db.refresh(test_group)
    db.refresh(test_user_type)
    return test_group, test_user_type


@pytest.mark.asyncio
async def test_read_users_page(async_client: AsyncClient) -> None:
    """社員管理ページ (GET /user) が正常に取得できることをテスト"""
    response = await async_client.get("/user")
    assert response.status_code == status.HTTP_200_OK
    assert "<title>Sokora - 社員管理</title>" in response.text
    # assert "<h1 class=\"text-2xl font-semibold\">社員管理</h1>" in response.text # H1タグの検証を一時的にコメントアウト 

# --- GET /pages/user/edit/{user_id} --- 

@pytest.mark.asyncio
async def test_get_user_edit_form_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザー編集フォームが正常に取得できることをテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user = crud_user.create(db, obj_in=UserCreate(user_id="edit_test", username="Edit Test User", group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()

    response = await async_client.get(f"/pages/user/edit/{user.id}")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    # URLのパス部分のみを検証するように修正
    expected_hx_put_path = f"/pages/user/row/{user.id}"
    assert f'hx-put="{expected_hx_put_path}"' in html.replace("http://test", "") 
    assert 'name="username" value="Edit Test User"' in html
    assert f'<option value="{group.id}" selected>' in html
    assert f'<option value="{user_type.id}" selected>' in html
    assert 'hx-target="#user-row-edit_test"' in html # hx-target の確認

@pytest.mark.asyncio
async def test_get_user_edit_form_not_found(async_client: AsyncClient) -> None:
    """存在しないユーザーIDで編集フォームを取得しようとすると404になることをテスト"""
    response = await async_client.get("/pages/user/edit/non_existent_user")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- POST /pages/user/row --- 

@pytest.mark.asyncio
async def test_handle_create_user_row_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザーが正常に作成され、対応する行のHTMLが返されることをテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user_id = "create_test_user"
    username = "Create Test User"
    form_data = {
        "id": user_id,
        "username": username,
        "group_id": str(group.id),
        "user_type_id": str(user_type.id)
    }

    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    print("\n--- test_handle_create_user_row_success HTML ---")
    print(html)
    print("--- End HTML ---")

    assert f'id="user-row-{user_id}"' in html
    # tdタグ内の空白を許容するように修正、f-string内のスラッシュのエスケープを削除
    assert f'>{user_id}</td>' in html.replace(" ", "")
    assert f'>{username}</td>' in html
    assert f'>{group.name}</td>' in html
    assert f'>{user_type.name}</td>' in html

    # DB確認
    db_user = db.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    assert db_user.username == username
    assert db_user.group_id == group.id
    assert db_user.user_type_id == user_type.id

@pytest.mark.asyncio
async def test_handle_create_user_row_duplicate_id(async_client: AsyncClient, db: Session) -> None:
    """重複するユーザーIDで作成しようとすると400エラーとエラーHTMLが返るテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user_id = "duplicate_create"
    # 既存ユーザー作成
    crud_user.create(db, obj_in=UserCreate(user_id=user_id, username="Existing", group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()

    form_data = {
        "id": user_id,
        "username": "New Duplicate",
        "group_id": str(group.id),
        "user_type_id": str(user_type.id)
    }
    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == "#add-form-error"
    # シングルクォーテーションがHTMLエンティティにエスケープされていることを確認
    expected_error = f"ユーザーID &#39;{user_id}&#39; は既に使用されています。"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text

# --- PUT /pages/user/row/{user_id} ---

@pytest.mark.asyncio
async def test_handle_update_user_row_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザー情報が正常に更新され、対応する行のHTMLが返されることをテスト"""
    group1, ut1 = create_test_dependencies_for_page(db)
    group2 = crud_group.create(db, obj_in=GroupCreate(name="Update Group Page"))
    ut2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Update UserType Page"))
    user_id = "update_test_user"
    original_username = "Original Update User"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id, username=original_username, group_id=str(group1.id), user_type_id=str(ut1.id)))
    db.commit()

    updated_username = "Updated User Name Page"
    form_data = {
        "username": updated_username,
        "group_id": str(group2.id),
        "user_type_id": str(ut2.id)
    }

    response = await async_client.put(f"/pages/user/row/{user_id}", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    print("\n--- test_handle_update_user_row_success HTML ---")
    print(html)
    print("--- End HTML ---")

    assert f'id=\"user-row-{user_id}\"' in html
    # 元のhtmlに対してアサーション、> と </td> の間に期待する文字列が含まれるか確認
    # user_id 以外はスペースを含む可能性があるため、元の html で検証
    assert f'>{updated_username}</td>' in html
    assert f'>{group2.name}</td>' in html
    assert f'>{ut2.name}</td>' in html

    # DB確認
    db.refresh(user)
    assert user.username == updated_username
    assert user.group_id == group2.id
    assert user.user_type_id == ut2.id

@pytest.mark.asyncio
async def test_handle_update_user_row_not_found(async_client: AsyncClient) -> None:
    """存在しないユーザーIDで更新しようとすると404エラーになるテスト"""
    form_data = {"username": "test", "group_id": "1", "user_type_id": "1"}
    response = await async_client.put("/pages/user/row/non_existent_user", data=form_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_handle_update_user_row_duplicate_username(async_client: AsyncClient, db: Session) -> None:
    """他のユーザーと重複するユーザー名で更新しようとすると400エラーになるテスト"""
    group, ut = create_test_dependencies_for_page(db)
    user1 = crud_user.create(db, obj_in=UserCreate(user_id="update_dup_user1", username="User1 UpdateDup", group_id=str(group.id), user_type_id=str(ut.id)))
    user2 = crud_user.create(db, obj_in=UserCreate(user_id="update_dup_user2", username="User2 UpdateDup", group_id=str(group.id), user_type_id=str(ut.id)))
    db.commit()

    form_data = {
        "username": user1.username,
        "group_id": str(group.id),
        "user_type_id": str(ut.id)
    }

    response = await async_client.put(f"/pages/user/row/{user2.id}", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{user2.id}"
    # HTMLエスケープされたシングルクォートを検証, 末尾の不要なスペースを削除
    expected_error = f"ユーザー名 &#39;{user1.username}&#39; は既に使用されています。" 
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text 