import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import location_service
from app.tests.utils.utils import random_lower_string

# テスト用の依存データを作成するヘルパー
def create_test_location(db: Session, name: str) -> models.Location:
    location_in = schemas.location.LocationCreate(name=name)
    return crud.location.create(db=db, obj_in=location_in)

def test_validate_location_creation_success(db: Session) -> None:
    """勤怠種別作成バリデーション成功（重複なし）"""
    location_in = schemas.location.LocationCreate(name=random_lower_string())
    # 例外が発生しないことを確認
    location_service.validate_location_creation(db, location_in=location_in)

def test_validate_location_creation_fail_duplicate_name(db: Session) -> None:
    """勤怠種別作成バリデーション失敗（名前重複）"""
    existing_name = random_lower_string()
    create_test_location(db, name=existing_name)
    db.commit()

    location_in = schemas.location.LocationCreate(name=existing_name)
    with pytest.raises(HTTPException) as excinfo:
        location_service.validate_location_creation(db, location_in=location_in)
    assert excinfo.value.status_code == 400
    assert "既に存在します" in excinfo.value.detail

def test_validate_location_creation_fail_empty_name(db: Session) -> None:
    """勤怠種別作成バリデーション失敗（名前が空）"""
    location_in = schemas.location.LocationCreate(name="")
    with pytest.raises(HTTPException) as excinfo:
        location_service.validate_location_creation(db, location_in=location_in)
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_validate_location_update_success(db: Session) -> None:
    """勤怠種別更新バリデーション成功"""
    # 更新対象と、別名の勤怠種別を作成
    location_to_update = create_test_location(db, name=random_lower_string())
    other_location = create_test_location(db, name=random_lower_string())
    db.commit()

    # ケース1: 存在しない名前に更新
    update_in_new_name = schemas.location.LocationUpdate(name=random_lower_string())
    location_service.validate_location_update(
        db, location_id_to_update=int(location_to_update.id), location_in=update_in_new_name
    )

    # ケース2: 自分自身の名前に更新（変更なし）
    update_in_same_name = schemas.location.LocationUpdate(name=str(location_to_update.name))
    location_service.validate_location_update(
        db, location_id_to_update=int(location_to_update.id), location_in=update_in_same_name
    )

def test_validate_location_update_fail_duplicate_name(db: Session) -> None:
    """勤怠種別更新バリデーション失敗（他勤怠種別と名前重複）"""
    location_to_update = create_test_location(db, name=random_lower_string())
    other_location = create_test_location(db, name=random_lower_string())
    db.commit()

    update_in = schemas.location.LocationUpdate(name=str(other_location.name))
    with pytest.raises(HTTPException) as excinfo:
        location_service.validate_location_update(
            db, location_id_to_update=int(location_to_update.id), location_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "既に使用されています" in excinfo.value.detail

def test_validate_location_update_fail_empty_name(db: Session) -> None:
    """勤怠種別更新バリデーション失敗（名前が空）"""
    location_to_update = create_test_location(db, name=random_lower_string())
    db.commit()

    update_in = schemas.location.LocationUpdate(name="")
    with pytest.raises(HTTPException) as excinfo:
        location_service.validate_location_update(
            db, location_id_to_update=int(location_to_update.id), location_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_create_location_with_validation_success(db: Session) -> None:
    """バリデーション付き勤怠種別作成成功"""
    location_name = random_lower_string()
    location_in = schemas.location.LocationCreate(name=location_name)

    created_location = location_service.create_location_with_validation(db, location_in=location_in)
    assert created_location
    assert created_location.name == location_name

    # DBでも確認
    db_location = db.query(models.Location).filter(models.Location.name == location_name).first()
    assert db_location
    assert db_location.id == created_location.id

def test_create_location_with_validation_fail(db: Session) -> None:
    """バリデーション付き勤怠種別作成失敗（重複）"""
    existing_name = random_lower_string()
    create_test_location(db, name=existing_name)
    db.commit()

    location_in = schemas.location.LocationCreate(name=existing_name)
    with pytest.raises(HTTPException):
        location_service.create_location_with_validation(db, location_in=location_in)

def test_update_location_with_validation_success(db: Session) -> None:
    """バリデーション付き勤怠種別更新成功"""
    location_to_update = create_test_location(db, name=random_lower_string())
    db.commit()

    new_name = random_lower_string()
    location_in_update = schemas.location.LocationUpdate(name=new_name)

    updated_location = location_service.update_location_with_validation(
        db, location_id=int(location_to_update.id), location_in=location_in_update
    )
    assert updated_location
    assert updated_location.id == location_to_update.id
    assert updated_location.name == new_name

    # DBでも確認
    db.refresh(updated_location)
    assert updated_location.name == new_name

def test_update_location_with_validation_fail_duplicate(db: Session) -> None:
    """バリデーション付き勤怠種別更新失敗（他勤怠種別と重複）"""
    location_to_update = create_test_location(db, name=random_lower_string())
    other_location = create_test_location(db, name=random_lower_string())
    db.commit()

    location_in_update = schemas.location.LocationUpdate(name=str(other_location.name))
    with pytest.raises(HTTPException):
        location_service.update_location_with_validation(
            db, location_id=int(location_to_update.id), location_in=location_in_update
        )

def test_update_location_with_validation_fail_not_found(db: Session) -> None:
    """バリデーション付き勤怠種別更新失敗（対象が存在しない）"""
    non_existent_id = 99999
    location_in_update = schemas.location.LocationUpdate(name=random_lower_string())
    with pytest.raises(HTTPException) as excinfo:
        location_service.update_location_with_validation(
            db, location_id=non_existent_id, location_in=location_in_update
        )
    assert excinfo.value.status_code == 404 # crud.get_or_404 で発生 