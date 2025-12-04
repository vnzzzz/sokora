import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import user_type_service
from app.tests.utils.utils import random_lower_string

# テスト用の依存データを作成するヘルパー (必要であれば conftest.py に移動)
def create_test_user_type(db: Session, name: str) -> models.UserType:
    user_type_in = schemas.user_type.UserTypeCreate(name=name)
    return crud.user_type.create(db=db, obj_in=user_type_in)

def test_validate_user_type_creation_success(db: Session) -> None:
    """社員種別作成バリデーション成功（重複なし）"""
    user_type_in = schemas.user_type.UserTypeCreate(name=random_lower_string())
    # 例外が発生しないことを確認
    user_type_service.validate_user_type_creation(db, user_type_in=user_type_in)

def test_validate_user_type_creation_fail_duplicate_name(db: Session) -> None:
    """社員種別作成バリデーション失敗（名前重複）"""
    existing_name = random_lower_string()
    create_test_user_type(db, name=existing_name)
    db.commit()

    user_type_in = schemas.user_type.UserTypeCreate(name=existing_name)
    with pytest.raises(HTTPException) as excinfo:
        user_type_service.validate_user_type_creation(db, user_type_in=user_type_in)
    assert excinfo.value.status_code == 400
    assert "既に存在します" in excinfo.value.detail

def test_validate_user_type_creation_fail_empty_name(db: Session) -> None:
    """社員種別作成バリデーション失敗（名前が空）"""
    user_type_in = schemas.user_type.UserTypeCreate(name="")
    with pytest.raises(HTTPException) as excinfo:
        user_type_service.validate_user_type_creation(db, user_type_in=user_type_in)
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_validate_user_type_update_success(db: Session) -> None:
    """社員種別更新バリデーション成功"""
    # 更新対象と、別名の社員種別を作成
    user_type_to_update = create_test_user_type(db, name=random_lower_string())
    create_test_user_type(db, name=random_lower_string())
    db.commit()

    # ケース1: 存在しない名前に更新
    update_in_new_name = schemas.user_type.UserTypeUpdate(name=random_lower_string())
    user_type_service.validate_user_type_update(
        db, user_type_id_to_update=int(user_type_to_update.id), user_type_in=update_in_new_name
    )

    # ケース2: 自分自身の名前に更新（変更なし）
    update_in_same_name = schemas.user_type.UserTypeUpdate(name=str(user_type_to_update.name))
    user_type_service.validate_user_type_update(
        db, user_type_id_to_update=int(user_type_to_update.id), user_type_in=update_in_same_name
    )

def test_validate_user_type_update_fail_duplicate_name(db: Session) -> None:
    """社員種別更新バリデーション失敗（他社員種別と名前重複）"""
    user_type_to_update = create_test_user_type(db, name=random_lower_string())
    other_user_type = create_test_user_type(db, name=random_lower_string())
    db.commit()

    update_in = schemas.user_type.UserTypeUpdate(name=str(other_user_type.name))
    with pytest.raises(HTTPException) as excinfo:
        user_type_service.validate_user_type_update(
            db, user_type_id_to_update=int(user_type_to_update.id), user_type_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "既に使用されています" in excinfo.value.detail

def test_validate_user_type_update_fail_empty_name(db: Session) -> None:
    """社員種別更新バリデーション失敗（名前が空）"""
    user_type_to_update = create_test_user_type(db, name=random_lower_string())
    db.commit()

    update_in = schemas.user_type.UserTypeUpdate(name="")
    with pytest.raises(HTTPException) as excinfo:
        user_type_service.validate_user_type_update(
            db, user_type_id_to_update=int(user_type_to_update.id), user_type_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_create_user_type_with_validation_success(db: Session) -> None:
    """バリデーション付き社員種別作成成功"""
    user_type_name = random_lower_string()
    user_type_in = schemas.user_type.UserTypeCreate(name=user_type_name)

    created_user_type = user_type_service.create_user_type_with_validation(db, user_type_in=user_type_in)
    assert created_user_type
    assert created_user_type.name == user_type_name

    # DBでも確認
    db_user_type = db.query(models.UserType).filter(models.UserType.name == user_type_name).first()
    assert db_user_type
    assert db_user_type.id == created_user_type.id

def test_create_user_type_with_validation_fail(db: Session) -> None:
    """バリデーション付き社員種別作成失敗（重複）"""
    existing_name = random_lower_string()
    create_test_user_type(db, name=existing_name)
    db.commit()

    user_type_in = schemas.user_type.UserTypeCreate(name=existing_name)
    with pytest.raises(HTTPException):
        user_type_service.create_user_type_with_validation(db, user_type_in=user_type_in)

def test_update_user_type_with_validation_success(db: Session) -> None:
    """バリデーション付き社員種別更新成功"""
    user_type_to_update = create_test_user_type(db, name=random_lower_string())
    db.commit()

    new_name = random_lower_string()
    user_type_in_update = schemas.user_type.UserTypeUpdate(name=new_name)

    updated_user_type = user_type_service.update_user_type_with_validation(
        db, user_type_id=int(user_type_to_update.id), user_type_in=user_type_in_update
    )
    assert updated_user_type
    assert updated_user_type.id == user_type_to_update.id
    assert updated_user_type.name == new_name

    # DBでも確認
    db.refresh(updated_user_type)
    assert updated_user_type.name == new_name

def test_update_user_type_with_validation_fail_duplicate(db: Session) -> None:
    """バリデーション付き社員種別更新失敗（他社員種別と重複）"""
    user_type_to_update = create_test_user_type(db, name=random_lower_string())
    other_user_type = create_test_user_type(db, name=random_lower_string())
    db.commit()

    user_type_in_update = schemas.user_type.UserTypeUpdate(name=str(other_user_type.name))
    with pytest.raises(HTTPException):
        user_type_service.update_user_type_with_validation(
            db, user_type_id=int(user_type_to_update.id), user_type_in=user_type_in_update
        )

def test_update_user_type_with_validation_fail_not_found(db: Session) -> None:
    """バリデーション付き社員種別更新失敗（対象が存在しない）"""
    non_existent_id = 99999
    user_type_in_update = schemas.user_type.UserTypeUpdate(name=random_lower_string())
    with pytest.raises(HTTPException) as excinfo:
        user_type_service.update_user_type_with_validation(
            db, user_type_id=non_existent_id, user_type_in=user_type_in_update
        )
    assert excinfo.value.status_code == 404 # crud.get_or_404 で発生 
