"""Attendance schema behavior tests."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.attendance import AttendanceCreate


def test_attendance_create_parses_iso_date_string() -> None:
    attendance = AttendanceCreate(
        user_id="test_user",
        date="2024-01-15",  # type: ignore[arg-type] - validate pre-parsing input
        location_id=1,
    )

    assert attendance.date == date(2024, 1, 15)


def test_attendance_create_rejects_invalid_date_string() -> None:
    with pytest.raises(ValidationError) as exc_info:
        AttendanceCreate(
            user_id="test_user",
            date="invalid-date",  # type: ignore[arg-type] - validate invalid input
            location_id=1,
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "日付形式が無効です" in str(errors[0]["ctx"]["error"])
