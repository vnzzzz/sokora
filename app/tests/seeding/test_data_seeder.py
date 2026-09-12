from collections import Counter
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Attendance, CustomHoliday, Group, Location, User, UserType
from scripts.seeding.data_seeder import (
    LEAVE_CATEGORY,
    OTHER_CATEGORY,
    WORK_CATEGORY,
    bootstrap_core_data,
    seed_attendance,
)

_REFERENCE_DATE = date(2026, 9, 12)
_OFFICE_LOCATION_NAMES = {
    "東京オフィス",
    "横浜オフィス",
    "大阪オフィス",
    "サテライトオフィス",
}


def test_demo_seed_builds_expected_master_shape(db: Session) -> None:
    created = bootstrap_core_data(db, reference_date=_REFERENCE_DATE)

    assert created == {
        "groups": 5,
        "user_types": 5,
        "locations": 18,
        "custom_holidays": 4,
        "users": 50,
    }

    groups = list(db.scalars(select(Group)).all())
    user_types = list(db.scalars(select(UserType)).all())
    users = list(db.scalars(select(User)).all())
    locations = list(db.scalars(select(Location)).all())
    custom_holidays = list(db.scalars(select(CustomHoliday)).all())

    assert len(groups) == 5
    assert len(user_types) == 5
    assert len(users) == 50
    assert Counter(int(user.group_id) for user in users) == {
        int(group.id): 10 for group in groups
    }
    assert Counter(str(location.category) for location in locations) == {
        WORK_CATEGORY: 10,
        LEAVE_CATEGORY: 3,
        OTHER_CATEGORY: 5,
    }

    seed_window_start = _REFERENCE_DATE - timedelta(days=60)
    seed_window_end = _REFERENCE_DATE + timedelta(days=60)
    assert len(custom_holidays) == 4
    assert all(
        seed_window_start <= holiday.date <= seed_window_end
        for holiday in custom_holidays
    )
    assert all(holiday.date.weekday() < 5 for holiday in custom_holidays)


def test_persona_seed_exercises_hybrid_categories_and_holiday_work(
    db: Session,
) -> None:
    bootstrap_core_data(db, reference_date=_REFERENCE_DATE)
    created = seed_attendance(
        db,
        days_back=60,
        days_forward=60,
        reference_date=_REFERENCE_DATE,
    )

    assert created

    locations = list(db.scalars(select(Location)).all())
    location_by_id = {int(location.id): location for location in locations}
    category_counts = Counter(
        str(location_by_id[int(attendance.location_id)].category)
        for attendance in created
    )
    assert category_counts[WORK_CATEGORY] > 0
    assert category_counts[LEAVE_CATEGORY] > 0
    assert category_counts[OTHER_CATEGORY] > 0

    location_name_counts = Counter(
        str(location_by_id[int(attendance.location_id)].name)
        for attendance in created
    )
    office_count = sum(
        location_name_counts[name] for name in _OFFICE_LOCATION_NAMES
    )
    remote_count = location_name_counts["テレワーク"]
    hybrid_total = office_count + remote_count
    assert hybrid_total > 0
    assert 0.40 <= remote_count / hybrid_total <= 0.60

    custom_holiday_dates = set(db.scalars(select(CustomHoliday.date)).all())
    holiday_work_records = [
        attendance
        for attendance in created
        if str(location_by_id[int(attendance.location_id)].name) == "休日出勤"
    ]
    assert holiday_work_records
    assert any(
        attendance.date.weekday() >= 5 or attendance.date in custom_holiday_dates
        for attendance in holiday_work_records
    )


def test_attendance_seed_is_deterministic_and_idempotent(db: Session) -> None:
    bootstrap_core_data(db, reference_date=_REFERENCE_DATE)

    first = seed_attendance(
        db,
        days_back=14,
        days_forward=14,
        reference_date=_REFERENCE_DATE,
        random_seed=12345,
    )
    first_signature = sorted(
        (str(record.user_id), record.date, int(record.location_id)) for record in first
    )

    assert (
        seed_attendance(
            db,
            days_back=14,
            days_forward=14,
            reference_date=_REFERENCE_DATE,
            random_seed=12345,
        )
        == []
    )

    db.execute(delete(Attendance))
    db.commit()

    recreated = seed_attendance(
        db,
        days_back=14,
        days_forward=14,
        reference_date=_REFERENCE_DATE,
        random_seed=12345,
    )
    recreated_signature = sorted(
        (str(record.user_id), record.date, int(record.location_id))
        for record in recreated
    )

    assert recreated_signature == first_signature
