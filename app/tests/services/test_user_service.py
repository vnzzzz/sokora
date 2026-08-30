import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.schemas.user_type import UserTypeCreate
from app.services import user_service
from app.tests.crud.test_crud_user import db_with_data
from app.tests.utils.utils import random_lower_string


def test_get_user_by_username(db_with_data: Session) -> None:
    """ユーザー名でユーザーを取得するテスト"""
    db = db_with_data
    # ユーザーを作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    # None チェックを先に実行
    assert group is not None
    assert user_type is not None
    user_in = schemas.UserCreate(
        id="testuser1", username="Test User One", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user = crud.user.create(db=db, obj_in=user_in)

    found_user = user_service.get_user_by_username(db, username=str(user.username))
    assert found_user
    assert found_user.id == user.id
    assert found_user.username == user.username

    not_found_user = user_service.get_user_by_username(db, username="nonexistentuser")
    assert not_found_user is None

def test_validate_dependencies_success(db_with_data: Session) -> None:
    """依存関係（グループ、社員種別）の検証が成功するテスト"""
    db = db_with_data
    # db_with_data フィクスチャで作成されたデータを取得
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    user_service.validate_dependencies(db, group_id=int(group.id), user_type_id=int(user_type.id))

def test_validate_dependencies_fail(db_with_data: Session) -> None:
    """依存関係の検証が失敗するテスト (存在しないID)"""
    db = db_with_data
    # db_with_data フィクスチャで作成されたデータを取得
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type

    with pytest.raises(HTTPException) as excinfo_group:
        user_service.validate_dependencies(db, group_id=9999, user_type_id=int(user_type.id))
    assert excinfo_group.value.status_code == 400
    assert "グループID" in excinfo_group.value.detail

    with pytest.raises(HTTPException) as excinfo_type:
        user_service.validate_dependencies(db, group_id=int(group.id), user_type_id=9999)
    assert excinfo_type.value.status_code == 400
    assert "社員種別ID" in excinfo_type.value.detail

def test_validate_user_creation_success(db_with_data: Session) -> None:
    """ユーザー作成バリデーション成功（重複なし）"""
    db = db_with_data
    # db_with_data フィクスチャで作成されたデータを取得
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type

    user_in = schemas.UserCreate(
        id=random_lower_string(8),
        username=random_lower_string(10),
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    user_service.validate_user_creation(db, user_in=user_in)

def test_validate_user_creation_fail_duplicate_id(db_with_data: Session) -> None:
    """ユーザー作成バリデーション失敗（ID重複）"""
    db = db_with_data
    # ユーザーを作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    existing_user_in = schemas.UserCreate(
        id="existing_user", username="Existing User Name", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    existing_user = crud.user.create(db=db, obj_in=existing_user_in)

    user_in = schemas.UserCreate(
        id=str(existing_user.id),
        username=random_lower_string(10),
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    with pytest.raises(HTTPException) as excinfo:
        user_service.validate_user_creation(db, user_in=user_in)
    assert excinfo.value.status_code == 400
    assert "ユーザーID" in excinfo.value.detail

def test_validate_user_creation_fail_duplicate_username(db_with_data: Session) -> None:
    """ユーザー作成バリデーション失敗（ユーザー名重複）"""
    db = db_with_data
    # ユーザーを作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    existing_user_in = schemas.UserCreate(
        id="another_user", username="Existing UserName", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    existing_user = crud.user.create(db=db, obj_in=existing_user_in)

    user_in = schemas.UserCreate(
        id=random_lower_string(8),
        username=str(existing_user.username),
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    with pytest.raises(HTTPException) as excinfo:
        user_service.validate_user_creation(db, user_in=user_in)
    assert excinfo.value.status_code == 400
    assert "ユーザー名" in excinfo.value.detail

def test_create_user_with_validation_success(db_with_data: Session) -> None:
    """バリデーション付きユーザー作成成功"""
    db = db_with_data
    # db_with_data フィクスチャで作成されたデータを取得
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type

    user_id = random_lower_string(8)
    username = random_lower_string(10)
    user_in = schemas.UserCreate(
        id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )

    created_user = user_service.create_user_with_validation(db, user_in=user_in)
    assert created_user
    assert created_user.id == user_id
    assert created_user.username == username
    assert created_user.group_id == group.id
    assert created_user.user_type_id == user_type.id

def test_create_user_with_validation_fail(db_with_data: Session) -> None:
    """バリデーション付きユーザー作成失敗（重複ID）"""
    db = db_with_data
    # ユーザーを作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    existing_user_in = schemas.UserCreate(
        id="one_more_user", username="One More User Name", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    existing_user = crud.user.create(db=db, obj_in=existing_user_in)

    user_in = schemas.UserCreate(
        id=str(existing_user.id),
        username=random_lower_string(10),
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    with pytest.raises(HTTPException):
        user_service.create_user_with_validation(db, user_in=user_in)


def test_update_user_with_validation_success(db_with_data: Session) -> None:
    """バリデーション付きユーザー更新成功"""
    db = db_with_data
    # ユーザーを作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    user_to_update_in = schemas.UserCreate(
        id="user_to_update", username="User To Update Name", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user_to_update = crud.user.create(db=db, obj_in=user_to_update_in)

    new_group = crud.group.create(db, obj_in=schemas.GroupCreate(name=random_lower_string()))
    new_user_type = crud.user_type.create(db, obj_in=UserTypeCreate(name=random_lower_string()))
    db.commit()

    new_username = random_lower_string(10)
    user_in_update = schemas.UserUpdate(
        username=new_username,
        group_id=int(new_group.id),
        user_type_id=int(new_user_type.id)
    )

    updated_user = user_service.update_user_with_validation(
        db, user_id=str(user_to_update.id), user_in=user_in_update
    )
    assert updated_user
    assert updated_user.id == user_to_update.id
    assert updated_user.username == new_username
    assert updated_user.group_id == new_group.id
    assert updated_user.user_type_id == new_user_type.id

def test_update_user_with_validation_fail_duplicate_username(db_with_data: Session) -> None:
    """バリデーション付きユーザー更新失敗（他ユーザーとユーザー名重複）"""
    db = db_with_data
    # ユーザーを2人作成
    group = db.query(models.Group).filter(models.Group.name == "Test Group").first()
    user_type = db.query(models.UserType).filter(models.UserType.name == "Test Type").first()
    assert group and user_type
    user1_in = schemas.UserCreate(
        id="user1", username="User One Name", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user1 = crud.user.create(db=db, obj_in=user1_in)
    user2_in = schemas.UserCreate(
        id="user2", username="User Two Name", group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user2 = crud.user.create(db=db, obj_in=user2_in)

    user_in_update = schemas.UserUpdate(
        username=str(user1.username),
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )

    with pytest.raises(HTTPException) as excinfo:
        user_service.update_user_with_validation(db, user_id=str(user2.id), user_in=user_in_update)
    assert excinfo.value.status_code == 400
    assert "ユーザー名" in excinfo.value.detail 