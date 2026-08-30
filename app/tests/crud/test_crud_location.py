import pytest
from sqlalchemy.orm import Session

from app import crud
from app.schemas.location import LocationCreate, LocationUpdate # 推測
from app.tests.utils.utils import random_lower_string


def test_create_location(db: Session) -> None:
    """新しいロケーションを作成するテスト"""
    name = random_lower_string()
    location_in = LocationCreate(name=name) # 推測
    location = crud.location.create(db=db, obj_in=location_in)
    assert location.name == name
    assert hasattr(location, "id")

def test_get_location(db: Session) -> None:
    """IDでロケーションを取得するテスト"""
    name = random_lower_string()
    location_in = LocationCreate(name=name) # 推測
    location = crud.location.create(db=db, obj_in=location_in)
    location_2 = crud.location.get(db=db, id=location.id)
    assert location_2
    assert location.name == location_2.name
    assert location.id == location_2.id

def test_update_location(db: Session) -> None:
    """ロケーション名を更新するテスト"""
    name = random_lower_string()
    location_in = LocationCreate(name=name) # 推測
    location = crud.location.create(db=db, obj_in=location_in)

    new_name = random_lower_string()
    location_in_update = LocationUpdate(name=new_name) # 推測
    location_updated = crud.location.update(db=db, db_obj=location, obj_in=location_in_update)

    assert location_updated.name == new_name
    assert location_updated.id == location.id

def test_remove_location(db: Session) -> None:
    """ロケーションを削除するテスト"""
    name = random_lower_string()
    location_in = LocationCreate(name=name) # 推測
    location = crud.location.create(db=db, obj_in=location_in)
    location_id = int(location.id) # キャスト

    removed_location = crud.location.remove(db=db, id=location_id)
    location_after_remove = crud.location.get(db=db, id=location_id)

    assert removed_location.id == location_id
    assert location_after_remove is None 