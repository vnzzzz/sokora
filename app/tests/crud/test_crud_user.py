import pytest
from sqlalchemy.orm import Session

from app import crud
from app.models import Group as GroupModel
from app.models import UserType as UserTypeModel
from app.schemas.group import GroupCreate
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.user_type import UserTypeCreate
from app.tests.utils.utils import random_lower_string


@pytest.fixture(scope="function")
def db_with_data(db: Session) -> Session:
    """テストに必要な基本データを投入したDBセッション"""
    group_in = GroupCreate(name="Test Group")
    crud.group.create(db=db, obj_in=group_in)
    user_type_in = UserTypeCreate(name="Test Type")
    crud.user_type.create(db=db, obj_in=user_type_in)
    return db


def test_create_user(db_with_data: Session) -> None:
    """新しいユーザーを作成するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Test User Name"
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = (
        db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    )
    assert group and user_type

    user_in = UserCreate(
        id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id),
    )
    user = crud.user.create(db=db, obj_in=user_in)
    assert user.id == user_id
    assert user.username == username
    assert user.group_id == group.id
    assert user.user_type_id == user_type.id


def test_get_user(db_with_data: Session) -> None:
    """IDでユーザーを取得するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Get Test User"
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = (
        db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    )
    assert group and user_type

    user_in = UserCreate(
        id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id),
    )
    user = crud.user.create(db=db, obj_in=user_in)
    user_2 = crud.user.get(db=db, id=user.id)
    assert user_2
    assert user.id == user_2.id
    assert user.username == user_2.username


def test_update_user(db_with_data: Session) -> None:
    """ユーザー情報を更新するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Update User"
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = (
        db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    )
    assert group and user_type

    user_in = UserCreate(
        id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id),
    )
    user = crud.user.create(db=db, obj_in=user_in)

    new_username = "Updated User Name"
    new_group_in = GroupCreate(name="New Test Group")
    new_group = crud.group.create(db=db, obj_in=new_group_in)
    new_user_type_in = UserTypeCreate(name="New Test Type")
    new_user_type = crud.user_type.create(db=db, obj_in=new_user_type_in)
    db.commit()

    user_in_update = UserUpdate(
        username=new_username,
        group_id=int(new_group.id),
        user_type_id=int(new_user_type.id),
    )

    crud.user.update(db=db, db_obj=user, obj_in=user_in_update)
    db.commit()

    user_updated_from_db = crud.user.get(db=db, id=user.id)

    assert user_updated_from_db is not None
    assert user_updated_from_db.id == user_id
    assert user_updated_from_db.username == new_username
    assert user_updated_from_db.group_id == new_group.id
    assert user_updated_from_db.user_type_id == new_user_type.id
