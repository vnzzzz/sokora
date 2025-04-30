import pytest
from sqlalchemy.orm import Session

from app import crud
from app.schemas.user_type import UserTypeCreate, UserTypeUpdate
from app.tests.utils.utils import random_lower_string


def test_create_user_type(db: Session) -> None:
    """新しいユーザータイプを作成するテスト"""
    name = random_lower_string()
    user_type_in = UserTypeCreate(name=name)
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)
    assert user_type.name == name
    assert hasattr(user_type, "id")

def test_get_user_type(db: Session) -> None:
    """IDでユーザータイプを取得するテスト"""
    name = random_lower_string()
    user_type_in = UserTypeCreate(name=name)
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)
    user_type_2 = crud.user_type.get(db=db, id=user_type.id)
    assert user_type_2
    assert user_type.name == user_type_2.name
    assert user_type.id == user_type_2.id

def test_update_user_type(db: Session) -> None:
    """ユーザータイプ名を更新するテスト"""
    name = random_lower_string()
    user_type_in = UserTypeCreate(name=name)
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)

    new_name = random_lower_string()
    user_type_in_update = UserTypeUpdate(name=new_name)
    user_type_updated = crud.user_type.update(db=db, db_obj=user_type, obj_in=user_type_in_update)

    assert user_type_updated.name == new_name
    assert user_type_updated.id == user_type.id

def test_remove_user_type(db: Session) -> None:
    """ユーザータイプを削除するテスト"""
    name = random_lower_string()
    user_type_in = UserTypeCreate(name=name)
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)
    user_type_id = int(user_type.id) # キャスト

    removed_user_type = crud.user_type.remove(db=db, id=user_type_id)
    user_type_after_remove = crud.user_type.get(db=db, id=user_type_id)

    assert removed_user_type.id == user_type_id
    assert user_type_after_remove is None 