"""Read models for master-management pages."""

from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app import crud, models


@dataclass(frozen=True)
class UserMasterPageViewModel:
    users: list[models.User]
    groups: list[models.Group]
    user_types: list[models.UserType]
    grouped_users: dict[str, list[models.User]]
    group_names: list[str]


@dataclass(frozen=True)
class LocationMasterPageViewModel:
    locations: list[models.Location]
    category_names: list[str]
    grouped_locations: dict[str, list[models.Location]]


def get_user_master_page_view_model(db: Session) -> UserMasterPageViewModel:
    """Build the employee master list without router-side N+1 lookups/grouping."""
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
            group_order = int(group.order) if group is not None and group.order is not None else 0
            group_id = int(group.id) if group is not None and group.id is not None else 0
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
    """Group attendance-location masters for the list template."""
    locations = crud.location.get_multi(db)
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
