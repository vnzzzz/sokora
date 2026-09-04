"""master管理画面のDB readをtemplate向けview modelへ編成する。

routerからrelationship eager-load、grouping、表示順決定を分離し、Jinja側で追加queryや
mutable groupingを行わないためのread boundaryである。
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app import crud, models


@dataclass(frozen=True)
class UserMasterPageViewModel:
    """user master pageのread contract。

    ``users`` はgroup/user typeをeager-load済み、``grouped_users`` は表示用にgroup名で
    partition済み、``group_names`` がその表示順を定義する。templateは独自query/sortを
    追加せず、このprojectionをそのまま利用する。
    """

    users: list[models.User]
    groups: list[models.Group]
    user_types: list[models.UserType]
    grouped_users: dict[str, list[models.User]]
    group_names: list[str]


@dataclass(frozen=True)
class LocationMasterPageViewModel:
    """勤怠種別master pageのcategory grouping contract。

    ``locations`` はCRUD queryのcategory/order/ID順を維持し、category名は最初に現れた順で
    ``category_names`` へ記録する。``grouped_locations`` 内のrow順も元query順を保つ。
    """

    locations: list[models.Location]
    category_names: list[str]
    grouped_locations: dict[str, list[models.Location]]


def get_user_master_page_view_model(db: Session) -> UserMasterPageViewModel:
    """user master listを固定されたread patternと表示順で構築する。

    user/group/user typeを計3 queryで取得し、user relationshipは最初のqueryでeager-loadして
    templateアクセスによるN+1を避ける。groupは明示orderを優先し、order未設定/未分類を後段へ
    送り、同値はpersistent ID/nameで安定化する。group内userは社員種別ID、username、user ID
    の順でsortする。
    """
    users = (
        db.query(models.User)
        .options(joinedload(models.User.group), joinedload(models.User.user_type))
        .all()
    )
    groups = crud.group.get_multi(db)
    user_types = crud.user_type.get_multi(db)

    grouped_users: dict[str, list[models.User]] = {}
    group_sort_keys: dict[str, tuple[bool, int, int, str]] = {}

    for user in users:
        group = user.group
        group_name = str(group.name) if group is not None else "未分類"
        grouped_users.setdefault(group_name, []).append(user)

        if group_name not in group_sort_keys:
            group_order = (
                int(group.order) if group is not None and group.order is not None else 0
            )
            group_id = (
                int(group.id) if group is not None and group.id is not None else 0
            )
            group_sort_keys[group_name] = (
                group is None or group.order is None,
                group_order,
                group_id,
                group_name,
            )

    for group_users in grouped_users.values():
        group_users.sort(
            key=lambda user: (
                int(user.user_type_id),
                str(user.username),
                str(user.id),
            )
        )

    group_names = sorted(grouped_users, key=group_sort_keys.__getitem__)
    return UserMasterPageViewModel(
        users=users,
        groups=groups,
        user_types=user_types,
        grouped_users=grouped_users,
        group_names=group_names,
    )


def get_location_master_page_view_model(db: Session) -> LocationMasterPageViewModel:
    """CRUD queryのdisplay orderを保ったまま勤怠種別をcategory別へpartitionする。

    category未設定は表示上だけ「未分類」へ正規化する。category/group内の順序は
    ``crud.location.list_all`` が決定したcategory → order → IDをそのまま維持し、この
    serviceで別のsort ruleを重ねない。
    """
    locations = crud.location.list_all(db)
    category_names: list[str] = []
    grouped_locations: dict[str, list[models.Location]] = {}

    for location in locations:
        category = str(location.category) if location.category else "未分類"
        if category not in grouped_locations:
            category_names.append(category)
            grouped_locations[category] = []
        grouped_locations[category].append(location)

    return LocationMasterPageViewModel(
        locations=locations,
        category_names=category_names,
        grouped_locations=grouped_locations,
    )
