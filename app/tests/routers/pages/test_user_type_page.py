import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session
import re # 正規表現モジュールをインポート
import json

# モデル、スキーマ、CRUD をインポート
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type


@pytest.mark.asyncio
async def test_read_user_types_page(async_client: AsyncClient, db: Session) -> None:
    """社員種別管理ページ (GET /user_types) が正常に取得でき、データが表示されることをテスト"""
    # Test data setup
    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType Page Test A"))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType Page Test B"))
    db.commit()

    response = await async_client.get("/user_types")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    assert "<title>Sokora - 社員種別管理</title>" in html

    # 社員種別データがテーブルに表示されていることを確認
    assert re.search(rf'<tr\s+.*?id="user-type-row-{user_type1.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="user-type-name-{user_type1.id}">{re.escape(str(user_type1.name))}<\/span>', html) is not None
    assert re.search(rf'<tr\s+.*?id="user-type-row-{user_type2.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="user-type-name-{user_type2.id}">{re.escape(str(user_type2.name))}<\/span>', html) is not None

    # 編集ボタンの hx-get 属性を確認
    assert f'hx-get="/pages/user_type/edit/{user_type1.id}"' in html
    # 削除ボタンの hx-delete 属性を確認
    expected_delete_url_t1 = f"/api/user_types/{user_type1.id}"
    delete_button_html_t1 = f'hx-delete="{expected_delete_url_t1}"'
    assert delete_button_html_t1 in html, f"Delete button with correct hx-delete for user_type {user_type1.id} not found"


@pytest.mark.asyncio
async def test_get_user_type_edit_form_success(async_client: AsyncClient, db: Session) -> None:
    """社員種別編集フォームが正常に取得できることをテスト"""
    user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="Edit UserType Form Test"))
    db.commit()

    response = await async_client.get(f"/pages/user_type/edit/{user_type.id}")
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # フォームの基本的な属性を確認
    assert f'id="edit-form-user-type-{user_type.id}"' in html
    assert f'hx-put="/pages/user_type/row/{user_type.id}"' in html
    assert 'hx-indicator="#loading-indicator"' in html

    # 社員種別名 input の存在と value を確認
    assert re.search(r'<input[^>]*name="name"[^>]*>', html) is not None, "Input field for name not found"
    assert f'value="{user_type.name}"' in html, "Input field does not contain correct value"

    # 保存ボタンとキャンセルボタンの存在を確認
    assert re.search(r'<button\s+type="submit".*?>保存<\/button>', html) is not None
    assert re.search(r'<button\s+type="button".*?@click="showEditModal\s*=\s*false".*?>キャンセル<\/button>', html) is not None


@pytest.mark.asyncio
async def test_get_user_type_edit_form_not_found(async_client: AsyncClient) -> None:
    """存在しない社員種別IDで編集フォームを取得しようとすると404になることをテスト"""
    response = await async_client.get("/pages/user_type/edit/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- POST /pages/user_type/row --- 

@pytest.mark.asyncio
async def test_handle_create_user_type_row_success(async_client: AsyncClient, db: Session) -> None:
    """社員種別が正常に作成され、対応する行のHTMLが返されることをテスト"""
    user_type_name = "Create UserType Row Test"
    form_data = {"name": user_type_name}

    response = await async_client.post("/pages/user_type/row", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # Find the created user_type to get its ID
    db_user_type = db.query(UserType).filter(UserType.name == user_type_name).first()
    assert db_user_type is not None
    user_type_id = db_user_type.id

    assert f'id="user-type-row-{user_type_id}"' in html
    assert f'<span id="user-type-name-{user_type_id}">{user_type_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"社員種別 {user_type_name} を追加しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

@pytest.mark.asyncio
async def test_handle_create_user_type_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """重複する社員種別名で作成しようとすると400エラーとエラーHTMLが返るテスト"""
    existing_name = "Duplicate Create Name UT"
    crud_user_type.create(db, obj_in=UserTypeCreate(name=existing_name))
    db.commit()

    form_data = {"name": existing_name}
    response = await async_client.post("/pages/user_type/row", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = "この社員種別名は既に存在します"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

# --- PUT /pages/user_type/row/{user_type_id} ---

@pytest.mark.asyncio
async def test_handle_update_user_type_row_success(async_client: AsyncClient, db: Session) -> None:
    """社員種別情報が正常に更新され、対応する行のHTMLが返されることをテスト"""
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name="Original Update Name UT"))
    db.commit()
    user_type_id = user_type_to_update.id

    updated_name = "Successfully Updated Name UT"
    form_data = {"name": updated_name}

    response = await async_client.put(f"/pages/user_type/row/{user_type_id}", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    assert f'id="user-type-row-{user_type_id}"' in html
    assert f'<span id="user-type-name-{user_type_id}">{updated_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"社員種別 {updated_name} を更新しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

    # DB確認
    db.refresh(user_type_to_update)
    assert user_type_to_update.name == updated_name

@pytest.mark.asyncio
async def test_handle_update_user_type_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """他の社員種別と重複する社員種別名で更新しようとすると400エラーになるテスト"""
    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Update UserType 1"))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Existing UserType Name"))
    db.commit()
    user_type1_id = user_type1.id
    existing_name = user_type2.name

    form_data = {"name": existing_name}
    response = await async_client.put(f"/pages/user_type/row/{user_type1_id}", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{user_type1_id}"
    expected_error = "この社員種別名は既に使用されています"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

@pytest.mark.asyncio
async def test_handle_update_user_type_row_not_found(async_client: AsyncClient) -> None:
    """存在しない社員種別IDで更新しようとすると404エラーになるテスト"""
    form_data = {"name": "Update Non Existent UT"}
    response = await async_client.put("/pages/user_type/row/99999", data=form_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND 