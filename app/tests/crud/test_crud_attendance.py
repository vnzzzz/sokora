import pytest
from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta

from app import crud
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.models import User as UserModel, Location as LocationModel, Group as GroupModel, UserType as UserTypeModel
from app.schemas.user import UserCreate
from app.schemas.group import GroupCreate
from app.schemas.user_type import UserTypeCreate
from app.schemas.location import LocationCreate
from app.tests.utils.utils import random_lower_string


@pytest.fixture(scope="function")
def db_with_attendance_data(db: Session) -> Session:
    """勤怠テストに必要なユーザーとロケーションデータを投入"""
    # グループ作成
    group_in = GroupCreate(name="Attendance Test Group")
    group = crud.group.create(db=db, obj_in=group_in)
    # ユーザータイプ作成
    user_type_in = UserTypeCreate(name="Attendance Test Type")
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)
    # ユーザー作成
    user_id = random_lower_string(8)
    username = "Attendance Test User"
    user_in = UserCreate(
        id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    crud.user.create(db=db, obj_in=user_in)

    # テスト用ロケーション作成
    location_in_office = LocationCreate(name="Test Location Office")
    crud.location.create(db=db, obj_in=location_in_office)
    location_in_remote = LocationCreate(name="Test Location Remote")
    crud.location.create(db=db, obj_in=location_in_remote)

    return db

def test_create_attendance(db_with_attendance_data: Session) -> None:
    """新しい勤怠記録を作成するテスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    attendance_date = date.today()

    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id)
    )
    attendance = crud.attendance.create(db=db, obj_in=attendance_in)

    assert attendance.user_id == user.id
    assert attendance.date == attendance_date
    assert attendance.location_id == location.id
    assert hasattr(attendance, "id")

def test_get_attendance(db_with_attendance_data: Session) -> None:
    """IDで勤怠記録を取得するテスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    attendance_date = date.today()
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id)
    )
    attendance = crud.attendance.create(db=db, obj_in=attendance_in)
    attendance_2 = crud.attendance.get(db=db, id=attendance.id)

    assert attendance_2
    assert attendance.id == attendance_2.id
    assert attendance.user_id == attendance_2.user_id
    assert attendance.date == attendance_2.date

def test_update_attendance(db_with_attendance_data: Session) -> None:
    """勤怠記録を更新するテスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    remote_location = db.query(LocationModel).filter(LocationModel.name == "Test Location Remote").first()
    assert user and location and remote_location

    attendance_date = date.today()
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id)
    )
    attendance = crud.attendance.create(db=db, obj_in=attendance_in)

    attendance_in_update = AttendanceUpdate(
        location_id=int(remote_location.id)
    )

    attendance_updated = crud.attendance.update(db=db, db_obj=attendance, obj_in=attendance_in_update)

    assert attendance_updated.id == attendance.id
    assert attendance_updated.location_id == remote_location.id
    assert attendance_updated.date == attendance.date
    assert attendance_updated.user_id == attendance.user_id

def test_remove_attendance(db_with_attendance_data: Session) -> None:
    """勤怠記録を削除するテスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    attendance_date = date.today()
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id)
    )
    attendance = crud.attendance.create(db=db, obj_in=attendance_in)
    attendance_id = int(attendance.id)

    removed_attendance = crud.attendance.remove(db=db, id=attendance_id)
    attendance_after_remove = crud.attendance.get(db=db, id=attendance_id)

    assert removed_attendance.id == attendance_id
    assert attendance_after_remove is None 