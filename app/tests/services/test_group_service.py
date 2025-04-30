# TODO: Implement tests for group service logic
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import group_service
from app.tests.utils.utils import random_lower_string

# テスト用の依存データを作成するヘルパー (必要であれば conftest.py に移動)
def create_test_group(db: Session, name: str) -> models.Group:
    group_in = schemas.GroupCreate(name=name)
    return crud.group.create(db=db, obj_in=group_in)

def test_validate_group_creation_success(db: Session) -> None:
    """グループ作成バリデーション成功（重複なし）"""
    group_in = schemas.GroupCreate(name=random_lower_string())
    # 例外が発生しないことを確認
    group_service.validate_group_creation(db, group_in=group_in)

def test_validate_group_creation_fail_duplicate_name(db: Session) -> None:
    """グループ作成バリデーション失敗（名前重複）"""
    existing_name = random_lower_string()
    create_test_group(db, name=existing_name)
    db.commit()

    group_in = schemas.GroupCreate(name=existing_name)
    with pytest.raises(HTTPException) as excinfo:
        group_service.validate_group_creation(db, group_in=group_in)
    assert excinfo.value.status_code == 400
    assert "既に存在します" in excinfo.value.detail

def test_validate_group_creation_fail_empty_name(db: Session) -> None:
    """グループ作成バリデーション失敗（名前が空）"""
    group_in = schemas.GroupCreate(name="")
    with pytest.raises(HTTPException) as excinfo:
        group_service.validate_group_creation(db, group_in=group_in)
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_validate_group_update_success(db: Session) -> None:
    """グループ更新バリデーション成功"""
    # 更新対象と、別名のグループを作成
    group_to_update = create_test_group(db, name=random_lower_string())
    other_group = create_test_group(db, name=random_lower_string())
    db.commit()

    # ケース1: 存在しない名前に更新
    update_in_new_name = schemas.GroupUpdate(name=random_lower_string())
    group_service.validate_group_update(
        db, group_id_to_update=int(group_to_update.id), group_in=update_in_new_name
    )

    # ケース2: 自分自身の名前に更新（変更なし）
    update_in_same_name = schemas.GroupUpdate(name=str(group_to_update.name))
    group_service.validate_group_update(
        db, group_id_to_update=int(group_to_update.id), group_in=update_in_same_name
    )

def test_validate_group_update_fail_duplicate_name(db: Session) -> None:
    """グループ更新バリデーション失敗（他グループと名前重複）"""
    group_to_update = create_test_group(db, name=random_lower_string())
    other_group = create_test_group(db, name=random_lower_string())
    db.commit()

    update_in = schemas.GroupUpdate(name=str(other_group.name))
    with pytest.raises(HTTPException) as excinfo:
        group_service.validate_group_update(
            db, group_id_to_update=int(group_to_update.id), group_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "既に使用されています" in excinfo.value.detail

def test_validate_group_update_fail_empty_name(db: Session) -> None:
    """グループ更新バリデーション失敗（名前が空）"""
    group_to_update = create_test_group(db, name=random_lower_string())
    db.commit()
    
    update_in = schemas.GroupUpdate(name="")
    with pytest.raises(HTTPException) as excinfo:
        group_service.validate_group_update(
            db, group_id_to_update=int(group_to_update.id), group_in=update_in
        )
    assert excinfo.value.status_code == 400
    assert "入力してください" in excinfo.value.detail

def test_create_group_with_validation_success(db: Session) -> None:
    """バリデーション付きグループ作成成功"""
    group_name = random_lower_string()
    group_in = schemas.GroupCreate(name=group_name)
    
    created_group = group_service.create_group_with_validation(db, group_in=group_in)
    assert created_group
    assert created_group.name == group_name

    # DBでも確認
    db_group = db.query(models.Group).filter(models.Group.name == group_name).first()
    assert db_group
    assert db_group.id == created_group.id

def test_create_group_with_validation_fail(db: Session) -> None:
    """バリデーション付きグループ作成失敗（重複）"""
    existing_name = random_lower_string()
    create_test_group(db, name=existing_name)
    db.commit()

    group_in = schemas.GroupCreate(name=existing_name)
    with pytest.raises(HTTPException):
        group_service.create_group_with_validation(db, group_in=group_in)

def test_update_group_with_validation_success(db: Session) -> None:
    """バリデーション付きグループ更新成功"""
    group_to_update = create_test_group(db, name=random_lower_string())
    db.commit()

    new_name = random_lower_string()
    group_in_update = schemas.GroupUpdate(name=new_name)

    updated_group = group_service.update_group_with_validation(
        db, group_id=int(group_to_update.id), group_in=group_in_update
    )
    assert updated_group
    assert updated_group.id == group_to_update.id
    assert updated_group.name == new_name

    # DBでも確認
    db.refresh(updated_group)
    assert updated_group.name == new_name

def test_update_group_with_validation_fail_duplicate(db: Session) -> None:
    """バリデーション付きグループ更新失敗（他グループと重複）"""
    group_to_update = create_test_group(db, name=random_lower_string())
    other_group = create_test_group(db, name=random_lower_string())
    db.commit()

    group_in_update = schemas.GroupUpdate(name=str(other_group.name))
    with pytest.raises(HTTPException):
        group_service.update_group_with_validation(
            db, group_id=int(group_to_update.id), group_in=group_in_update
        )

def test_update_group_with_validation_fail_not_found(db: Session) -> None:
    """バリデーション付きグループ更新失敗（対象が存在しない）"""
    non_existent_id = 99999
    group_in_update = schemas.GroupUpdate(name=random_lower_string())
    with pytest.raises(HTTPException) as excinfo:
        group_service.update_group_with_validation(
            db, group_id=non_existent_id, group_in=group_in_update
        )
    assert excinfo.value.status_code == 404 # crud.get_or_404 で発生 