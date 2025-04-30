import pytest
from sqlalchemy.orm import Session

from app import crud
from app.schemas.group import GroupCreate, GroupUpdate
from app.tests.utils.utils import random_lower_string


def test_create_group(db: Session) -> None:
    """新しいグループを作成するテスト"""
    name = random_lower_string()
    group_in = GroupCreate(name=name)
    group = crud.group.create(db=db, obj_in=group_in)
    assert group.name == name
    assert hasattr(group, "id")


def test_get_group(db: Session) -> None:
    """IDでグループを取得するテスト"""
    name = random_lower_string()
    group_in = GroupCreate(name=name)
    group = crud.group.create(db=db, obj_in=group_in)
    group_2 = crud.group.get(db=db, id=group.id)
    assert group_2
    assert group.name == group_2.name
    assert group.id == group_2.id


def test_update_group(db: Session) -> None:
    """グループ名を更新するテスト"""
    name = random_lower_string()
    group_in = GroupCreate(name=name)
    group = crud.group.create(db=db, obj_in=group_in)

    new_name = random_lower_string()
    group_in_update = GroupUpdate(name=new_name)
    group_updated = crud.group.update(db=db, db_obj=group, obj_in=group_in_update)

    assert group_updated.name == new_name
    assert group_updated.id == group.id

def test_remove_group(db: Session) -> None:
    """グループを削除するテスト"""
    name = random_lower_string()
    group_in = GroupCreate(name=name)
    group = crud.group.create(db=db, obj_in=group_in)
    group_id = int(group.id)

    removed_group = crud.group.remove(db=db, id=group_id)
    group_after_remove = crud.group.get(db=db, id=group_id)

    assert removed_group.id == group_id
    assert group_after_remove is None 