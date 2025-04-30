import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session
import re # 正規表現モジュールをインポート
import json

# モデル、スキーマ、CRUD をインポート
from app.models.location import Location
from app.schemas.location import LocationCreate
from app.crud.location import location as crud_location


@pytest.mark.asyncio
async def test_read_locations_page(async_client: AsyncClient, db: Session) -> None:
    """勤務場所管理ページ (GET /locations) が正常に取得でき、データが表示されることをテスト"""
    # Test data setup
    location1 = crud_location.create(db, obj_in=LocationCreate(name="Location Page Test A"))
    location2 = crud_location.create(db, obj_in=LocationCreate(name="Location Page Test B"))
    db.commit()

    response = await async_client.get("/locations")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    assert "<title>Sokora - 勤務場所管理</title>" in html

    # 勤務場所データがテーブルに表示されていることを確認
    assert re.search(rf'<tr\s+.*?id="location-row-{location1.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="location-name-{location1.id}">{re.escape(str(location1.name))}<\/span>', html) is not None
    assert re.search(rf'<tr\s+.*?id="location-row-{location2.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="location-name-{location2.id}">{re.escape(str(location2.name))}<\/span>', html) is not None

    # 編集ボタンの hx-get 属性を確認
    assert f'hx-get="/pages/location/edit/{location1.id}"' in html
    # 削除ボタンの hx-delete 属性を確認
    expected_delete_url_l1 = f"/api/locations/{location1.id}"
    delete_button_html_l1 = f'hx-delete="{expected_delete_url_l1}"'
    assert delete_button_html_l1 in html, f"Delete button with correct hx-delete for location {location1.id} not found"


@pytest.mark.asyncio
async def test_get_location_edit_form_success(async_client: AsyncClient, db: Session) -> None:
    """勤務場所編集フォームが正常に取得できることをテスト"""
    location = crud_location.create(db, obj_in=LocationCreate(name="Edit Location Form Test"))
    db.commit()

    response = await async_client.get(f"/pages/location/edit/{location.id}")
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # フォームの基本的な属性を確認
    assert f'id="edit-form-location-{location.id}"' in html
    assert f'hx-put="/pages/location/row/{location.id}"' in html
    assert 'hx-indicator="#loading-indicator"' in html

    # 勤務場所名 input の存在と value を確認
    assert re.search(r'<input[^>]*name="name"[^>]*>', html) is not None, "Input field for name not found"
    assert f'value="{location.name}"' in html, "Input field does not contain correct value"

    # 保存ボタンとキャンセルボタンの存在を確認
    assert re.search(r'<button\s+type="submit".*?>保存<\/button>', html) is not None
    assert re.search(r'<button\s+type="button".*?@click="showEditModal\s*=\s*false".*?>キャンセル<\/button>', html) is not None


@pytest.mark.asyncio
async def test_get_location_edit_form_not_found(async_client: AsyncClient) -> None:
    """存在しない勤務場所IDで編集フォームを取得しようとすると404になることをテスト"""
    response = await async_client.get("/pages/location/edit/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- POST /pages/location/row --- 

@pytest.mark.asyncio
async def test_handle_create_location_row_success(async_client: AsyncClient, db: Session) -> None:
    """勤務場所が正常に作成され、対応する行のHTMLが返されることをテスト"""
    location_name = "Create Location Row Test"
    form_data = {"name": location_name}

    response = await async_client.post("/pages/location/row", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # Find the created location to get its ID
    db_location = db.query(Location).filter(Location.name == location_name).first()
    assert db_location is not None
    location_id = db_location.id

    assert f'id="location-row-{location_id}"' in html
    assert f'<span id="location-name-{location_id}">{location_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"勤務場所 {location_name} を追加しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

@pytest.mark.asyncio
async def test_handle_create_location_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """重複する勤務場所名で作成しようとすると400エラーとエラーHTMLが返るテスト"""
    existing_name = "Duplicate Create Name Loc"
    crud_location.create(db, obj_in=LocationCreate(name=existing_name))
    db.commit()

    form_data = {"name": existing_name}
    response = await async_client.post("/pages/location/row", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = "この勤務場所名は既に存在します"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

# --- PUT /pages/location/row/{location_id} ---

@pytest.mark.asyncio
async def test_handle_update_location_row_success(async_client: AsyncClient, db: Session) -> None:
    """勤務場所情報が正常に更新され、対応する行のHTMLが返されることをテスト"""
    location_to_update = crud_location.create(db, obj_in=LocationCreate(name="Original Update Name Loc"))
    db.commit()
    location_id = location_to_update.id

    updated_name = "Successfully Updated Name Loc"
    form_data = {"name": updated_name}

    response = await async_client.put(f"/pages/location/row/{location_id}", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    assert f'id="location-row-{location_id}"' in html
    assert f'<span id="location-name-{location_id}">{updated_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"勤務場所 {updated_name} を更新しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

    # DB確認
    db.refresh(location_to_update)
    assert location_to_update.name == updated_name

@pytest.mark.asyncio
async def test_handle_update_location_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """他の勤務場所と重複する勤務場所名で更新しようとすると400エラーになるテスト"""
    location1 = crud_location.create(db, obj_in=LocationCreate(name="Update Location 1"))
    location2 = crud_location.create(db, obj_in=LocationCreate(name="Existing Location Name"))
    db.commit()
    location1_id = location1.id
    existing_name = location2.name

    form_data = {"name": existing_name}
    response = await async_client.put(f"/pages/location/row/{location1_id}", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{location1_id}"
    expected_error = "この勤務場所名は既に使用されています"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

@pytest.mark.asyncio
async def test_handle_update_location_row_not_found(async_client: AsyncClient) -> None:
    """存在しない勤務場所IDで更新しようとすると404エラーになるテスト"""
    form_data = {"name": "Update Non Existent Loc"}
    response = await async_client.put("/pages/location/row/99999", data=form_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND 