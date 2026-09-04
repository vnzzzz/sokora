"""attendance analysisのmulti-query consistency regression tests。"""

from datetime import date
from types import SimpleNamespace

from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app import crud
from app.services import attendance_analysis_service


def test_analysis_defers_attendance_for_location_not_seen_by_master_read(
    db: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    """途中commitで後続queryだけが新locationを見ても500にせず次readへ反映する。"""
    existing_location = SimpleNamespace(
        id=101,
        name="Existing Location",
        category="Office",
        order=10,
    )
    concurrent_location = SimpleNamespace(
        id=202,
        name="Concurrent Location",
        category="Office",
        order=20,
    )
    visible_locations = [existing_location]

    attendances = [
        SimpleNamespace(
            user_id="analysis-user",
            location_id=existing_location.id,
            date=date(2032, 5, 10),
            note="existing",
        ),
        # PostgreSQL READ COMMITTEDでは、location query完了後に別transactionが
        # location + attendanceをcommitすると、後続attendance queryだけがこのrowを
        # 観測し得る。先行master readに無いrowは現在responseへ混ぜない。
        SimpleNamespace(
            user_id="analysis-user",
            location_id=concurrent_location.id,
            date=date(2032, 5, 11),
            note="concurrent",
        ),
    ]

    monkeypatch.setattr(
        crud.user,
        "get_all_users_with_details",
        lambda _db: [("Analysis User", "analysis-user", "Group", "Type")],
    )
    monkeypatch.setattr(
        crud.location,
        "get_multi",
        lambda _db: list(visible_locations),
    )
    monkeypatch.setattr(
        crud.attendance,
        "list_for_period",
        lambda _db, *, start_date, end_date: list(attendances),
    )

    first = attendance_analysis_service.get_attendance_analysis_data(
        db,
        month="2032-05",
    )

    assert first["summary"]["total_attendance_days"] == 1
    assert first["summary"]["location_totals"] == {101: 1}
    assert first["users"]["analysis-user"]["location_counts"] == {101: 1}
    assert [int(location.id) for location in first["locations"]] == [101]

    # 次requestのmaster readがcommit済みlocationを観測した後は、同じattendance rowも
    # 通常どおり集計対象へ入る。
    visible_locations.append(concurrent_location)

    second = attendance_analysis_service.get_attendance_analysis_data(
        db,
        month="2032-05",
    )

    assert second["summary"]["total_attendance_days"] == 2
    assert second["summary"]["location_totals"] == {101: 1, 202: 1}
    assert second["users"]["analysis-user"]["location_counts"] == {101: 1, 202: 1}
    assert [int(location.id) for location in second["locations"]] == [101, 202]
