"""
勤怠データシーダー
================

fresh SQLiteやローカル開発環境向けに、組織master・カスタム祝日・勤怠記録を含む
demo datasetを生成する。

自動seedは ``app.db.session.initialize_database`` がfresh file-backed SQLiteと判定した場合だけ
呼ばれる。既存DBへのdefault同期はこのmoduleの責務ではなく、各tableに既存dataがあれば
そのtableのdefault masterは追加しない。

実行方法:
プロジェクトルートディレクトリから以下のコマンドで実行してください。
`uv run python -m scripts.seeding.data_seeder --days-back <日数> --days-forward <日数>`
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import SessionLocal, init_db
from app.models.attendance import Attendance
from app.models.custom_holiday import CustomHoliday
from app.models.group import Group
from app.models.location import Location
from app.models.user import User
from app.models.user_type import UserType
from app.utils.holiday_cache import get_holiday_name

WORK_CATEGORY = "勤務"
LEAVE_CATEGORY = "休暇"
OTHER_CATEGORY = "その他"
DEFAULT_RANDOM_SEED = 1722026

DEFAULT_GROUPS = [
    {"name": "プロダクト開発部", "order": 1},
    {"name": "営業部", "order": 2},
    {"name": "カスタマーサクセス部", "order": 3},
    {"name": "コーポレート部", "order": 4},
    {"name": "事業企画部", "order": 5},
]

DEFAULT_USER_TYPES = [
    {"name": "正社員", "order": 1},
    {"name": "契約社員", "order": 2},
    {"name": "パートタイム", "order": 3},
    {"name": "派遣社員", "order": 4},
    {"name": "インターン", "order": 5},
]

DEFAULT_LOCATIONS = [
    {"name": "東京オフィス", "category": WORK_CATEGORY, "order": 1},
    {"name": "横浜オフィス", "category": WORK_CATEGORY, "order": 2},
    {"name": "大阪オフィス", "category": WORK_CATEGORY, "order": 3},
    {"name": "テレワーク", "category": WORK_CATEGORY, "order": 4},
    {"name": "サテライトオフィス", "category": WORK_CATEGORY, "order": 5},
    {"name": "客先勤務", "category": WORK_CATEGORY, "order": 6},
    {"name": "国内出張", "category": WORK_CATEGORY, "order": 7},
    {"name": "海外出張", "category": WORK_CATEGORY, "order": 8},
    {"name": "夜勤", "category": WORK_CATEGORY, "order": 9},
    {"name": "休日出勤", "category": WORK_CATEGORY, "order": 10},
    {"name": "有給休暇", "category": LEAVE_CATEGORY, "order": 1},
    {"name": "午前休", "category": LEAVE_CATEGORY, "order": 2},
    {"name": "午後休", "category": LEAVE_CATEGORY, "order": 3},
    {"name": "夜勤明け休暇", "category": LEAVE_CATEGORY, "order": 4},
    {"name": "研修", "category": OTHER_CATEGORY, "order": 1},
    {"name": "健康診断", "category": OTHER_CATEGORY, "order": 2},
    {"name": "社内イベント", "category": OTHER_CATEGORY, "order": 3},
    {"name": "待機", "category": OTHER_CATEGORY, "order": 4},
    {"name": "その他", "category": OTHER_CATEGORY, "order": 5},
]

_SURNAMES = (
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "伊藤",
    "渡辺",
    "山本",
    "中村",
    "小林",
    "加藤",
)
_GIVEN_NAMES = ("悠斗", "美咲", "大輝", "結衣", "翔太")


def _build_default_users() -> list[dict[str, str]]:
    users: list[dict[str, str]] = []
    for group_index, group in enumerate(DEFAULT_GROUPS):
        for member_index in range(10):
            user_number = group_index * 10 + member_index + 1
            surname = _SURNAMES[member_index]
            given_name = _GIVEN_NAMES[(member_index + group_index) % len(_GIVEN_NAMES)]
            user_type = DEFAULT_USER_TYPES[
                (member_index + group_index) % len(DEFAULT_USER_TYPES)
            ]
            users.append(
                {
                    "id": f"U{user_number:03d}",
                    "username": f"{surname}{given_name}",
                    "group_name": str(group["name"]),
                    "user_type_name": str(user_type["name"]),
                }
            )
    return users


DEFAULT_USERS = _build_default_users()


@dataclass(frozen=True)
class AttendancePersona:
    """demo userへ割り当てる安定した勤務傾向。"""

    name: str
    remote_share: float
    field_work_rate: float
    night_work_rate: float
    weekday_attendance_rate: float
    leave_rate: float
    other_rate: float
    holiday_work_rate: float


ATTENDANCE_PERSONAS = (
    AttendancePersona(
        name="office_hybrid",
        remote_share=0.25,
        field_work_rate=0.02,
        night_work_rate=0.0,
        weekday_attendance_rate=0.97,
        leave_rate=0.05,
        other_rate=0.03,
        holiday_work_rate=0.015,
    ),
    AttendancePersona(
        name="remote_hybrid",
        remote_share=0.75,
        field_work_rate=0.01,
        night_work_rate=0.0,
        weekday_attendance_rate=0.96,
        leave_rate=0.05,
        other_rate=0.03,
        holiday_work_rate=0.01,
    ),
    AttendancePersona(
        name="balanced_hybrid",
        remote_share=0.50,
        field_work_rate=0.03,
        night_work_rate=0.0,
        weekday_attendance_rate=0.96,
        leave_rate=0.06,
        other_rate=0.04,
        holiday_work_rate=0.02,
    ),
    AttendancePersona(
        name="field",
        remote_share=0.50,
        field_work_rate=0.32,
        night_work_rate=0.0,
        weekday_attendance_rate=0.97,
        leave_rate=0.04,
        other_rate=0.03,
        holiday_work_rate=0.04,
    ),
    AttendancePersona(
        name="shift",
        remote_share=0.50,
        field_work_rate=0.02,
        night_work_rate=0.25,
        weekday_attendance_rate=0.95,
        leave_rate=0.05,
        other_rate=0.03,
        holiday_work_rate=0.18,
    ),
)

_OFFICE_LOCATION_WEIGHTS = {
    "東京オフィス": 0.50,
    "横浜オフィス": 0.20,
    "大阪オフィス": 0.10,
    "サテライトオフィス": 0.20,
}
_FIELD_LOCATION_WEIGHTS = {
    "客先勤務": 0.60,
    "国内出張": 0.30,
    "海外出張": 0.10,
}


def _next_weekday(day: date) -> date:
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def default_custom_holidays(reference_date: date) -> list[dict[str, object]]:
    """seed期間内へ4つのDB由来custom holidayを配置する。"""

    offsets_and_names = (
        (-42, "全社リフレッシュ休暇"),
        (-14, "創立記念日"),
        (21, "全社研修休業日"),
        (49, "特別休業日"),
    )
    return [
        {
            "date": _next_weekday(reference_date + timedelta(days=offset)),
            "name": name,
        }
        for offset, name in offsets_and_names
    ]


def bootstrap_core_data(
    db: Session,
    *,
    reference_date: date | None = None,
) -> dict[str, int]:
    """空のmaster tableへdemo組織・勤怠種別・custom holiday・userを投入する。"""

    reference_date = reference_date or date.today()
    created_counts = {
        "groups": 0,
        "user_types": 0,
        "locations": 0,
        "custom_holidays": 0,
        "users": 0,
    }

    groups = list(db.scalars(select(Group)).all())
    if not groups:
        groups = [Group(**group) for group in DEFAULT_GROUPS]
        db.add_all(groups)
        created_counts["groups"] = len(groups)

    user_types = list(db.scalars(select(UserType)).all())
    if not user_types:
        user_types = [UserType(**user_type) for user_type in DEFAULT_USER_TYPES]
        db.add_all(user_types)
        created_counts["user_types"] = len(user_types)

    locations = list(db.scalars(select(Location)).all())
    if not locations:
        locations = [Location(**location) for location in DEFAULT_LOCATIONS]
        db.add_all(locations)
        created_counts["locations"] = len(locations)

    custom_holidays = list(db.scalars(select(CustomHoliday)).all())
    if not custom_holidays:
        custom_holidays = [
            CustomHoliday(**holiday)
            for holiday in default_custom_holidays(reference_date)
        ]
        db.add_all(custom_holidays)
        created_counts["custom_holidays"] = len(custom_holidays)

    if any(count > 0 for count in created_counts.values()):
        db.commit()
        groups = list(db.scalars(select(Group)).all())
        user_types = list(db.scalars(select(UserType)).all())
        locations = list(db.scalars(select(Location)).all())

    users = list(db.scalars(select(User)).all())
    if not users:
        if not groups or not user_types:
            logger.error(
                "グループまたは社員種別の作成に失敗しました。ユーザーを投入できません。"
            )
        else:
            group_by_name = {str(group.name): group for group in groups}
            user_type_by_name = {
                str(user_type.name): user_type for user_type in user_types
            }
            for index, user in enumerate(DEFAULT_USERS):
                group = (
                    group_by_name.get(user["group_name"])
                    or groups[(index // 10) % len(groups)]
                )
                user_type = (
                    user_type_by_name.get(user["user_type_name"])
                    or user_types[index % len(user_types)]
                )
                db.add(
                    User(
                        id=user["id"],
                        username=user["username"],
                        group_id=int(group.id),
                        user_type_id=int(user_type.id),
                    )
                )
            db.commit()
            created_counts["users"] = len(DEFAULT_USERS)

    return created_counts


def _rng_for_day(*, random_seed: int, user_id: str, day: date) -> random.Random:
    return random.Random(f"{random_seed}:{user_id}:{day.isoformat()}")


def _weighted_named_location(
    rng: random.Random,
    locations_by_name: dict[str, Location],
    weights_by_name: dict[str, float],
) -> Location | None:
    candidates = [
        (locations_by_name[name], weight)
        for name, weight in weights_by_name.items()
        if name in locations_by_name
    ]
    if not candidates:
        return None
    return rng.choices(
        [candidate for candidate, _weight in candidates],
        weights=[weight for _candidate, weight in candidates],
        k=1,
    )[0]


def _choose_work_location(
    rng: random.Random,
    *,
    persona: AttendancePersona,
    locations_by_name: dict[str, Location],
    work_locations: list[Location],
) -> Location | None:
    special_roll = rng.random()

    if special_roll < persona.field_work_rate:
        field_location = _weighted_named_location(
            rng,
            locations_by_name,
            _FIELD_LOCATION_WEIGHTS,
        )
        if field_location is not None:
            return field_location
    elif special_roll < persona.field_work_rate + persona.night_work_rate:
        night_location = locations_by_name.get("夜勤")
        if night_location is not None:
            return night_location

    remote_location = locations_by_name.get("テレワーク")
    office_location = _weighted_named_location(
        rng,
        locations_by_name,
        _OFFICE_LOCATION_WEIGHTS,
    )
    if remote_location is not None and office_location is not None:
        return (
            remote_location if rng.random() < persona.remote_share else office_location
        )
    if remote_location is not None:
        return remote_location
    if office_location is not None:
        return office_location
    if work_locations:
        return rng.choice(work_locations)
    return None


def _is_holiday(day: date, custom_holiday_dates: set[date]) -> bool:
    return (
        day.weekday() >= 5 or day in custom_holiday_dates or bool(get_holiday_name(day))
    )


def seed_attendance(
    db: Session,
    days_back: int = 30,
    days_forward: int = 30,
    *,
    reference_date: date | None = None,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> list[Attendance]:
    """既存user/masterを使い、personaベースの再現可能なdemo勤怠を生成する。"""

    users = list(db.scalars(select(User).order_by(User.id)).all())
    if not users:
        logger.error("データベースにユーザーが存在しません。勤怠記録を生成できません。")
        return []

    locations = list(db.scalars(select(Location).order_by(Location.id)).all())
    if not locations:
        logger.error("データベースに勤怠種別が存在しません。勤怠記録を生成できません。")
        return []

    logger.info("%s 人のユーザーが見つかりました。", len(users))
    logger.info(
        "%s 個の勤怠種別が見つかりました: %s",
        len(locations),
        [location.name for location in locations],
    )

    existing_records = {
        (str(record.user_id), date.fromisoformat(str(record.date))): int(
            record.location_id
        )
        for record in db.scalars(select(Attendance)).all()
    }

    reference_date = reference_date or date.today()
    start_date = reference_date - timedelta(days=days_back)
    end_date = reference_date + timedelta(days=days_forward)
    custom_holiday_dates = {
        date.fromisoformat(str(holiday.date))
        for holiday in db.scalars(select(CustomHoliday)).all()
    }

    locations_by_name = {str(location.name): location for location in locations}
    locations_by_id = {int(location.id): location for location in locations}
    all_leave_locations = [
        location for location in locations if location.category == LEAVE_CATEGORY
    ]
    leave_locations = [
        location for location in all_leave_locations if location.name != "夜勤明け休暇"
    ]
    other_locations = [
        location for location in locations if location.category == OTHER_CATEGORY
    ]
    work_locations = [
        location for location in locations if location.category == WORK_CATEGORY
    ]
    if not work_locations:
        work_locations = [
            location
            for location in locations
            if location not in all_leave_locations and location not in other_locations
        ] or locations

    holiday_work_location = locations_by_name.get("休日出勤")
    post_night_leave_location = locations_by_name.get("夜勤明け休暇")
    created_records: list[Attendance] = []

    for user_index, user in enumerate(users):
        user_id = str(user.id)
        persona = ATTENDANCE_PERSONAS[user_index % len(ATTENDANCE_PERSONAS)]
        logger.info(
            "ユーザー %s (%s) の勤怠記録を生成中: persona=%s",
            user.username,
            user.id,
            persona.name,
        )

        for day_offset in range((end_date - start_date).days + 1):
            day = start_date + timedelta(days=day_offset)
            record_key = (user_id, day)
            if record_key in existing_records:
                continue

            previous_location_id = existing_records.get(
                (user_id, day - timedelta(days=1))
            )
            previous_location = (
                locations_by_id.get(previous_location_id)
                if previous_location_id is not None
                else None
            )
            chosen_location: Location | None = None

            if (
                previous_location is not None
                and previous_location.name == "夜勤"
                and post_night_leave_location is not None
            ):
                chosen_location = post_night_leave_location
            else:
                rng = _rng_for_day(
                    random_seed=random_seed,
                    user_id=user_id,
                    day=day,
                )

                if _is_holiday(day, custom_holiday_dates):
                    if rng.random() >= persona.holiday_work_rate:
                        continue
                    chosen_location = holiday_work_location or _choose_work_location(
                        rng,
                        persona=persona,
                        locations_by_name=locations_by_name,
                        work_locations=work_locations,
                    )
                else:
                    if rng.random() >= persona.weekday_attendance_rate:
                        continue

                    event_roll = rng.random()
                    if leave_locations and event_roll < persona.leave_rate:
                        chosen_location = rng.choice(leave_locations)
                    elif (
                        other_locations
                        and event_roll < persona.leave_rate + persona.other_rate
                    ):
                        chosen_location = rng.choice(other_locations)
                    else:
                        chosen_location = _choose_work_location(
                            rng,
                            persona=persona,
                            locations_by_name=locations_by_name,
                            work_locations=work_locations,
                        )

            if chosen_location is None:
                continue

            attendance = Attendance(
                user_id=user_id,
                date=day,
                location_id=int(chosen_location.id),
            )
            db.add(attendance)
            created_records.append(attendance)
            existing_records[record_key] = int(chosen_location.id)

    db.commit()
    logger.info("%s 件の勤怠記録をシードしました。", len(created_records))
    return created_records


def run_seeder(
    days_back: int = 60,
    days_forward: int = 30,
    skip_init: bool = False,
) -> dict[str, int]:
    """masterとattendanceのdemo dataを現在DBへseedする。"""

    if not skip_init:
        init_db()

    db = SessionLocal()
    try:
        reference_date = date.today()
        bootstrap_result = bootstrap_core_data(db, reference_date=reference_date)
        logger.info(
            "ベースデータの確認/作成: "
            "groups=%s, user_types=%s, locations=%s, custom_holidays=%s, users=%s",
            bootstrap_result["groups"],
            bootstrap_result["user_types"],
            bootstrap_result["locations"],
            bootstrap_result["custom_holidays"],
            bootstrap_result["users"],
        )

        user_count = len(list(db.scalars(select(User)).all()))
        location_count = len(list(db.scalars(select(Location)).all()))
        if user_count == 0 or location_count == 0:
            logger.error("必須データの作成に失敗しました。勤怠記録を生成できません。")
            return {"attendances": 0}

        attendances = seed_attendance(
            db,
            days_back=days_back,
            days_forward=days_forward,
            reference_date=reference_date,
        )
        return {**bootstrap_result, "attendances": len(attendances)}

    except Exception as exc:
        logger.error("シーダー実行中にエラーが発生しました: %s", exc, exc_info=True)
        db.rollback()
        return {"attendances": 0}
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="demo masterとpersonaベースの勤怠記録を追加します"
    )
    parser.add_argument(
        "--days-back", type=int, default=60, help="過去何日分のデータを生成するか"
    )
    parser.add_argument(
        "--days-forward", type=int, default=30, help="未来何日分のデータを生成するか"
    )

    args = parser.parse_args()

    print("勤怠データシーダーを実行中...")
    result = run_seeder(days_back=args.days_back, days_forward=args.days_forward)
    print("完了しました！")
    print(f"生成された勤怠記録: {result['attendances']} 件")
