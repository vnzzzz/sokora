import pytest
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Dict
from unittest.mock import patch, MagicMock

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


# カスタムメソッドのテスト
def test_get_by_user_and_date(db_with_attendance_data: Session) -> None:
    """ユーザーIDと日付で勤怠記録を取得するテスト"""
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
    created_attendance = crud.attendance.create(db=db, obj_in=attendance_in)

    # 存在する記録の取得
    found_attendance = crud.attendance.get_by_user_and_date(
        db=db, user_id=str(user.id), date=attendance_date
    )
    assert found_attendance
    assert found_attendance.id == created_attendance.id

    # 存在しない記録の取得
    future_date = attendance_date + timedelta(days=1)
    not_found = crud.attendance.get_by_user_and_date(
        db=db, user_id=str(user.id), date=future_date
    )
    assert not_found is None


def test_delete_attendance_custom(db_with_attendance_data: Session) -> None:
    """指定ユーザーと日付の勤怠記録削除テスト（カスタムメソッド）"""
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
    crud.attendance.create(db=db, obj_in=attendance_in)

    # 存在する記録の削除（delete_attendanceはコミットしないため、手動でコミット）
    result = crud.attendance.delete_attendance(
        db=db, user_id=str(user.id), date_obj=attendance_date
    )
    assert result is True
    db.commit()  # 削除をコミット

    # 削除した後、再度削除を試みる（存在しない記録の削除）
    result_not_found = crud.attendance.delete_attendance(
        db=db, user_id=str(user.id), date_obj=attendance_date
    )
    assert result_not_found is False


def test_delete_by_user_and_date(db_with_attendance_data: Session) -> None:
    """キャッシュクリア付きの勤怠記録削除テスト"""
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
    crud.attendance.create(db=db, obj_in=attendance_in)

    # キャッシュに擬似データを追加
    day_key = attendance_date.strftime("%Y-%m-%d")
    crud.attendance._day_data_cache[day_key] = {"test": []}

    # 削除実行（delete_by_user_and_dateもコミットしないため、手動でコミット）
    result = crud.attendance.delete_by_user_and_date(
        db=db, user_id=str(user.id), date_obj=attendance_date
    )
    assert result is True
    db.commit()  # 削除をコミット
    # キャッシュがクリアされていることを確認
    assert day_key not in crud.attendance._day_data_cache

    # 削除した後、再度削除を試みる（存在しない記録の削除）
    result_not_found = crud.attendance.delete_by_user_and_date(
        db=db, user_id=str(user.id), date_obj=attendance_date
    )
    assert result_not_found is False


def test_delete_attendances_by_user_id(db_with_attendance_data: Session) -> None:
    """ユーザーIDによる全勤怠記録削除テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    # 複数の勤怠記録を作成
    dates = [date.today(), date.today() - timedelta(days=1), date.today() - timedelta(days=2)]
    for test_date in dates:
        attendance_in = AttendanceCreate(
            user_id=str(user.id),
            date=test_date,
            location_id=int(location.id)
        )
        crud.attendance.create(db=db, obj_in=attendance_in)

    # 全削除実行
    deleted_count = crud.attendance.delete_attendances_by_user_id(
        db=db, user_id=str(user.id)
    )
    assert deleted_count == 3

    # 存在しないユーザーの削除
    deleted_count_zero = crud.attendance.delete_attendances_by_user_id(
        db=db, user_id="nonexistent"
    )
    assert deleted_count_zero == 0


@pytest.fixture
def analysis_seed(db: Session) -> Dict[str, Any]:
    """月次・年度集計のテストデータを投入"""
    dev_group = crud.group.create(db=db, obj_in=GroupCreate(name="開発部"))
    sales_group = crud.group.create(db=db, obj_in=GroupCreate(name="営業部"))

    full_time = crud.user_type.create(db=db, obj_in=UserTypeCreate(name="正社員"))
    contractor = crud.user_type.create(db=db, obj_in=UserTypeCreate(name="契約"))

    office = crud.location.create(db=db, obj_in=LocationCreate(name="東京オフィス", order=1))
    remote = crud.location.create(db=db, obj_in=LocationCreate(name="リモート", order=2))

    alice = crud.user.create(
        db=db,
        obj_in=UserCreate(
            id="U-ALICE",
            username="Alice",
            group_id=int(dev_group.id),
            user_type_id=int(full_time.id),
        ),
    )
    bob = crud.user.create(
        db=db,
        obj_in=UserCreate(
            id="U-BOB",
            username="Bob",
            group_id=int(sales_group.id),
            user_type_id=int(contractor.id),
        ),
    )

    def add_att(user_id: str, loc_id: int, y: int, m: int, d: int) -> None:
        crud.attendance.create(
            db=db,
            obj_in=AttendanceCreate(
                user_id=user_id,
                location_id=loc_id,
                date=date(y, m, d),
            ),
        )

    # 2024-05 (月次集計に含める)
    add_att("U-ALICE", int(office.id), 2024, 5, 2)
    add_att("U-ALICE", int(remote.id), 2024, 5, 10)
    add_att("U-BOB", int(remote.id), 2024, 5, 5)

    # 2024年度 (4月開始〜翌年3月) に含まれる追加分
    add_att("U-ALICE", int(office.id), 2024, 7, 1)
    add_att("U-BOB", int(remote.id), 2024, 12, 1)
    add_att("U-BOB", int(office.id), 2025, 2, 3)  # 同一年度内

    # 2023年度のデータ（年度集計では除外される）
    add_att("U-BOB", int(remote.id), 2024, 3, 15)

    return {
        "db": db,
        "users": {"alice": str(alice.id), "bob": str(bob.id)},
        "locations": {"office": int(office.id), "remote": int(remote.id)},
        "groups": {"dev": dev_group.name, "sales": sales_group.name},
    }


def test_analysis_monthly_counts_and_dates(analysis_seed: Dict[str, Any]) -> None:
    """月次集計で勤怠種別ごとの日数と日付が返る"""
    db = analysis_seed["db"]
    analysis = crud.attendance.get_attendance_analysis_data(db=db, month="2024-05")

    period = analysis["period"]
    assert period["mode"] == "month"
    assert period["label"] == "2024年5月"

    alice_id = analysis_seed["users"]["alice"]
    office_id = analysis_seed["locations"]["office"]
    remote_id = analysis_seed["locations"]["remote"]

    alice_data = analysis["users"][alice_id]
    assert alice_data["location_counts"][office_id] == 1
    assert alice_data["location_counts"][remote_id] == 1
    remote_dates = [d["date_str"] for d in alice_data["location_dates"][remote_id]]
    assert remote_dates == ["2024-05-10"]

    # グループ別集計も月次範囲で作成される
    dev_group = analysis_seed["groups"]["dev"]
    assert analysis["group_summary"][dev_group]["total_days"] == 2
    assert analysis["group_summary"][dev_group]["location_counts"][office_id] == 1


def test_analysis_fiscal_year_range_and_grouping(analysis_seed: Dict[str, Any]) -> None:
    """年度集計で4月〜翌3月のデータがまとめて集計され、グループ別サマリーも返る"""
    db = analysis_seed["db"]
    analysis = crud.attendance.get_attendance_analysis_data(db=db, fiscal_year=2024)

    period = analysis["period"]
    assert period["mode"] == "fiscal_year"
    assert period["start"] == date(2024, 4, 1)
    assert period["end"] == date(2025, 3, 31)

    bob_id = analysis_seed["users"]["bob"]
    office_id = analysis_seed["locations"]["office"]
    remote_id = analysis_seed["locations"]["remote"]

    bob_data = analysis["users"][bob_id]
    # 2024年度に含まれる出社が2日（5月と翌年2月）、3月のデータは除外
    assert bob_data["location_counts"][remote_id] == 2  # 5月・12月の2日分
    assert bob_data["location_counts"][office_id] == 1
    office_dates = [d["date_str"] for d in bob_data["location_dates"][office_id]]
    assert office_dates == ["2025-02-03"]

    # グループ別サマリーは全勤怠種別を合算
    sales_group = analysis_seed["groups"]["sales"]
    group_totals = analysis["group_summary"][sales_group]["location_counts"]
    assert group_totals[office_id] == 1
    assert group_totals[remote_id] == 2


def test_update_attendance_method(db_with_attendance_data: Session) -> None:
    """勤怠記録の作成・更新メソッドテスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    remote_location = db.query(LocationModel).filter(LocationModel.name == "Test Location Remote").first()
    assert user and location and remote_location

    attendance_date = date.today()

    # 新規作成
    created_attendance = crud.attendance.update_attendance(
        db=db, user_id=str(user.id), date_obj=attendance_date, 
        location_id=int(location.id), note="テスト備考"
    )
    assert created_attendance
    assert created_attendance.location_id == location.id
    assert created_attendance.note == "テスト備考"

    # 更新
    updated_attendance = crud.attendance.update_attendance(
        db=db, user_id=str(user.id), date_obj=attendance_date, 
        location_id=int(remote_location.id), note="更新後備考"
    )
    assert updated_attendance
    assert updated_attendance.id == created_attendance.id
    assert updated_attendance.location_id == remote_location.id
    assert updated_attendance.note == "更新後備考"


def test_update_user_entry_create(db_with_attendance_data: Session) -> None:
    """update_user_entry 新規作成テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    date_str = date.today().strftime("%Y-%m-%d")
    
    # 新規作成
    result = crud.attendance.update_user_entry(
        db=db, user_id=str(user.id), date_str=date_str, 
        location_id=int(location.id), note="新規テスト"
    )
    assert result is True

    # 作成されたか確認
    attendance = crud.attendance.get_by_user_and_date(
        db=db, user_id=str(user.id), date=date.today()
    )
    assert attendance
    assert attendance.note == "新規テスト"


def test_update_user_entry_delete(db_with_attendance_data: Session) -> None:
    """update_user_entry 削除テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    # 事前に勤怠記録を作成
    attendance_date = date.today()
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id)
    )
    crud.attendance.create(db=db, obj_in=attendance_in)

    date_str = attendance_date.strftime("%Y-%m-%d")
    
    # 削除 (location_id = -1)
    result = crud.attendance.update_user_entry(
        db=db, user_id=str(user.id), date_str=date_str, location_id=-1
    )
    assert result is True

    # 削除されたか確認
    attendance = crud.attendance.get_by_user_and_date(
        db=db, user_id=str(user.id), date=attendance_date
    )
    assert attendance is None


def test_update_user_entry_error_cases(db_with_attendance_data: Session) -> None:
    """update_user_entry エラーケーステスト"""
    db = db_with_attendance_data
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert location

    # 存在しないユーザー
    result = crud.attendance.update_user_entry(
        db=db, user_id="nonexistent", date_str="2023-01-01", location_id=int(location.id)
    )
    assert result is False

    # 無効な日付形式
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    assert user
    result = crud.attendance.update_user_entry(
        db=db, user_id=str(user.id), date_str="invalid-date", location_id=int(location.id)
    )
    assert result is False


def test_get_user_data(db_with_attendance_data: Session) -> None:
    """ユーザー勤怠データ取得テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    # 複数の勤怠記録を作成
    dates = [date.today(), date.today() - timedelta(days=1)]
    for test_date in dates:
        attendance_in = AttendanceCreate(
            user_id=str(user.id),
            date=test_date,
            location_id=int(location.id),
            note=f"備考{test_date}"
        )
        crud.attendance.create(db=db, obj_in=attendance_in)

    # データ取得
    user_data = crud.attendance.get_user_data(db=db, user_id=str(user.id))
    assert len(user_data) == 2
    assert all("date" in entry for entry in user_data)
    assert all("location_name" in entry for entry in user_data)
    assert all("note" in entry for entry in user_data)

    # 存在しないユーザー
    empty_data = crud.attendance.get_user_data(db=db, user_id="nonexistent")
    assert empty_data == []


def test_get_day_data(db_with_attendance_data: Session) -> None:
    """日別データ取得テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    attendance_date = date.today()
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=attendance_date,
        location_id=int(location.id),
        note="テスト備考"
    )
    crud.attendance.create(db=db, obj_in=attendance_in)

    day_str = attendance_date.strftime("%Y-%m-%d")
    
    # データ取得
    day_data = crud.attendance.get_day_data(db=db, day=day_str)
    assert "Test Location Office" in day_data
    users_list = day_data["Test Location Office"]
    assert len(users_list) == 1
    assert users_list[0]["user_name"] == "Attendance Test User"
    assert users_list[0]["note"] == "テスト備考"

    # キャッシュ機能テスト
    day_data_cached = crud.attendance.get_day_data(db=db, day=day_str)
    assert day_data_cached == day_data

    # 無効な日付
    invalid_data = crud.attendance.get_day_data(db=db, day="invalid-date")
    assert invalid_data == {}


def test_get_attendance_data_for_csv(db_with_attendance_data: Session) -> None:
    """CSV用データ取得テスト"""
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
    crud.attendance.create(db=db, obj_in=attendance_in)

    # 全データ取得
    csv_data = crud.attendance.get_attendance_data_for_csv(db=db)
    expected_key = f"{user.id}_{attendance_date.strftime('%Y-%m-%d')}"
    assert expected_key in csv_data
    assert csv_data[expected_key] == "Test Location Office"

    # 日付範囲指定
    start_date = attendance_date - timedelta(days=1)
    end_date = attendance_date + timedelta(days=1)
    csv_data_range = crud.attendance.get_attendance_data_for_csv(
        db=db, start_date=start_date, end_date=end_date
    )
    assert expected_key in csv_data_range


def test_get_attendance_analysis_data(db_with_attendance_data: Session) -> None:
    """勤怠集計データ取得テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    # テストデータ作成
    test_date = date(2023, 1, 15)  # 固定日付でテスト
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=test_date,
        location_id=int(location.id)
    )
    crud.attendance.create(db=db, obj_in=attendance_in)

    # 月指定での取得
    analysis_data = crud.attendance.get_attendance_analysis_data(
        db=db, month="2023-01"
    )
    assert analysis_data["month"] == "2023-01"
    assert analysis_data["month_name"] == "2023年1月"
    assert "users" in analysis_data
    assert "locations" in analysis_data
    assert "summary" in analysis_data

    # 月指定なしでの取得（現在月）
    current_analysis = crud.attendance.get_attendance_analysis_data(db=db)
    assert "month" in current_analysis
    assert "users" in current_analysis


def test_get_attendance_by_type_for_fiscal_year(db_with_attendance_data: Session) -> None:
    """年度別勤怠種別データ取得テスト"""
    db = db_with_attendance_data
    user = db.query(UserModel).filter(UserModel.username == "Attendance Test User").first()
    location = db.query(LocationModel).filter(LocationModel.name == "Test Location Office").first()
    assert user and location

    # テストデータ作成
    test_date = date(2023, 6, 15)  # 固定日付でテスト
    attendance_in = AttendanceCreate(
        user_id=str(user.id),
        date=test_date,
        location_id=int(location.id),
        note="年度テスト"
    )
    crud.attendance.create(db=db, obj_in=attendance_in)

    # 年度・勤怠種別指定での取得
    fiscal_data = crud.attendance.get_attendance_by_type_for_fiscal_year(
        db=db, location_id=int(location.id), year=2023
    )
    assert fiscal_data["year"] == 2023
    assert fiscal_data["location_id"] == location.id
    assert fiscal_data["location_name"] == "Test Location Office"
    assert "users_data" in fiscal_data
    assert "locations" in fiscal_data

    # パラメータなしでの取得
    default_fiscal = crud.attendance.get_attendance_by_type_for_fiscal_year(db=db)
    assert "year" in default_fiscal
    assert "users_data" in default_fiscal


# エラーハンドリングのテスト
@patch('app.crud.attendance.logger')
def test_error_handling_delete_attendances_by_user_id(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """delete_attendances_by_user_id エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # データベースエラーをシミュレート
    with patch.object(db, 'query') as mock_query:
        mock_query.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            crud.attendance.delete_attendances_by_user_id(db=db, user_id="test")
        
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_update_attendance(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """update_attendance エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # エラーをシミュレート
    with patch.object(crud.attendance, 'get_by_user_and_date') as mock_get:
        mock_get.side_effect = Exception("Database error")
        
        result = crud.attendance.update_attendance(
            db=db, user_id="test", date_obj=date.today(), location_id=1
        )
        assert result is None
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_get_user_data(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """get_user_data エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # データベースエラーをシミュレート
    with patch.object(db, 'query') as mock_query:
        mock_query.side_effect = Exception("Database error")
        
        result = crud.attendance.get_user_data(db=db, user_id="test")
        assert result == []
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_get_day_data(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """get_day_data エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # データベースエラーをシミュレート
    with patch.object(db, 'query') as mock_query:
        mock_query.side_effect = Exception("Database error")
        
        result = crud.attendance.get_day_data(db=db, day="2023-01-01")
        assert result == {}
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_get_attendance_data_for_csv(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """get_attendance_data_for_csv エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # データベースエラーをシミュレート
    with patch.object(db, 'query') as mock_query:
        mock_query.side_effect = Exception("Database error")
        
        result = crud.attendance.get_attendance_data_for_csv(db=db)
        assert result == {}
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_analysis_data(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """get_attendance_analysis_data エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # エラーをシミュレート - 正しいインスタンスメソッドをパッチ
    with patch('app.crud.user.user.get_all_users_with_details') as mock_users:
        mock_users.side_effect = Exception("Database error")
        
        result = crud.attendance.get_attendance_analysis_data(db=db, month="2023-01")
        assert result["month_name"] == "エラー"
        assert result["users"] == {}
        mock_logger.error.assert_called()


@patch('app.crud.attendance.logger')
def test_error_handling_fiscal_year_data(mock_logger: MagicMock, db_with_attendance_data: Session) -> None:
    """get_attendance_by_type_for_fiscal_year エラーハンドリングテスト"""
    db = db_with_attendance_data
    
    # エラーをシミュレート - 正しいインスタンスメソッドをパッチ
    with patch('app.crud.location.location.get_multi') as mock_locations:
        mock_locations.side_effect = Exception("Database error")
        
        result = crud.attendance.get_attendance_by_type_for_fiscal_year(db=db, year=2023)
        assert result["location_name"] == "エラー"
        assert result["users_data"] == {}
        mock_logger.error.assert_called() 
