import pytest
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app import crud
from app.crud.calendar import calendar_crud
from app.models import User as UserModel, Location as LocationModel, Attendance as AttendanceModel, Group as GroupModel, UserType as UserTypeModel
from app.schemas.attendance import AttendanceCreate
from app.schemas.user import UserCreate
from app.schemas.group import GroupCreate
from app.schemas.user_type import UserTypeCreate
from app.schemas.location import LocationCreate
from app.tests.utils.utils import random_lower_string


@pytest.fixture(scope="function")
def db_with_calendar_test_data(db: Session) -> Session:
    """カレンダーテスト用の追加勤怠データを作成"""
    # グループ作成
    group_in = GroupCreate(name="Calendar Test Group")
    group = crud.group.create(db=db, obj_in=group_in)
    # ユーザータイプ作成
    user_type_in = UserTypeCreate(name="Calendar Test Type")
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)
    # ユーザー作成
    user_id = random_lower_string(8)
    username = "Calendar Test User"
    user_in = UserCreate(
        user_id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    user = crud.user.create(db=db, obj_in=user_in)
    # ロケーション作成
    location_in = LocationCreate(name="Calendar Test Location")
    location = crud.location.create(db=db, obj_in=location_in)

    # 今月と先月、来月の日付を取得
    today = date.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    first_day_next_month = (first_day_this_month.replace(year=today.year + (today.month // 12), month=(today.month % 12) + 1)
                            if today.month < 12 else first_day_this_month.replace(year=today.year + 1, month=1))

    # テスト用勤怠データを作成
    dates_to_create = [
        first_day_prev_month,                   # 先月初日
        last_day_prev_month,                    # 先月末日
        first_day_this_month,                   # 今月初日
        first_day_this_month + timedelta(days=1), # 今月2日
        today,                                  # 今日
        first_day_next_month                    # 来月初日
    ]

    # 重複を排除するために set を使用
    unique_dates = set(dates_to_create)

    for dt in unique_dates:
        attendance_in = AttendanceCreate(
            user_id=str(user.id),
            date=dt,
            location_id=int(location.id)
        )
        crud.attendance.create(db=db, obj_in=attendance_in)

    return db

def test_get_month_attendances(db_with_calendar_test_data: Session) -> None:
    """指定期間内の勤怠データを取得するテスト"""
    db = db_with_calendar_test_data
    today = date.today()
    first_day = today.replace(day=1)
    # 月末日の計算 (calendar モジュールを使う方が堅牢)
    import calendar
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)

    attendances = calendar_crud.get_month_attendances(db=db, first_day=first_day, last_day=last_day)
    # 今月作成したデータ数 (1日、2日、今日（今日が1日or2日の場合は重複しない）)
    expected_count = 0
    if first_day <= first_day <= last_day: expected_count +=1
    if first_day <= first_day + timedelta(days=1) <= last_day: expected_count +=1
    if first_day <= today <= last_day and today.day > 2: expected_count +=1 # 今日が1,2日と重複しない場合のみカウント
    assert len(attendances) == expected_count
    for att in attendances:
        assert first_day <= att.date <= last_day

def test_count_day_attendances(db_with_calendar_test_data: Session) -> None:
    """指定日の勤怠データ数を取得するテスト"""
    db = db_with_calendar_test_data
    first_day_this_month = date.today().replace(day=1)
    target_date_1 = first_day_this_month # 1件のはず
    target_date_2 = first_day_this_month + timedelta(days=1) # 1件のはず
    target_date_no_data = first_day_this_month + timedelta(days=10) # 0件のはず

    count_1 = calendar_crud.count_day_attendances(db=db, target_date=target_date_1)
    count_2 = calendar_crud.count_day_attendances(db=db, target_date=target_date_2)
    count_no_data = calendar_crud.count_day_attendances(db=db, target_date=target_date_no_data)

    assert count_1 == 1
    assert count_2 == 1 # 2日のデータは1件になったはず
    assert count_no_data == 0

def test_get_month_attendance_counts(db_with_calendar_test_data: Session) -> None:
    """月内の日付ごとの勤怠データ数を取得するテスト"""
    db = db_with_calendar_test_data
    today = date.today()
    first_day = today.replace(day=1)
    import calendar
    _, last_day_num = calendar.monthrange(today.year, today.month)
    last_day = today.replace(day=last_day_num)

    counts = calendar_crud.get_month_attendance_counts(db=db, first_day=first_day, last_day=last_day)

    assert counts.get(1, 0) == 1 # 1日
    assert counts.get(2, 0) == 1 # 2日
    # 今日が1日か2日でない場合のみ、今日のデータをチェック
    if today.day > 2:
        assert counts.get(today.day, 0) == 1 # 今日
    # データがある日数は、今日が1日か2日かどうかで変わる
    expected_days_with_data = 0
    if first_day.day <= last_day.day: # 月初が月末より前（通常）
      if 1 >= first_day.day and 1 <= last_day.day: expected_days_with_data += 1
      if 2 >= first_day.day and 2 <= last_day.day: expected_days_with_data += 1
      if today.day > 2 and today.day >= first_day.day and today.day <= last_day.day: expected_days_with_data += 1
    assert len(counts) == expected_days_with_data 