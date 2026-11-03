"""グループ関連のvalidationとtransaction境界を提供するservice。"""

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.named_master_service import NamedMasterMessages, NamedMasterService

_group_master = NamedMasterService[
    models.Group,
    schemas.GroupCreate,
    schemas.GroupUpdate,
](
    crud=crud.group,
    get_by_name=lambda db, name: crud.group.get_by_name(db, name=name),
    get_id=lambda group: int(group.id),
    messages=NamedMasterMessages(
        required_name="グループ名を入力してください",
        duplicate_create="このグループ名は既に存在します",
        duplicate_update="このグループ名は既に使用されています",
        delete_integrity="利用中のグループは削除できません",
    ),
)


def validate_group_creation(db: Session, *, group_in: schemas.GroupCreate) -> None:
    """作成前に必須名と名前重複を検証する。

    Args:
        db: DB session。
        group_in: 作成予定のgroupデータ。

    Raises:
        HTTPException: group名が空または重複する場合。
    """
    _group_master.validate_creation(db, name=group_in.name)


def validate_group_update(
    db: Session, *, group_id_to_update: int, group_in: schemas.GroupUpdate
) -> None:
    """更新対象自身を除外してgroup名を検証する。

    Args:
        db: DB session。
        group_id_to_update: 更新対象group ID。
        group_in: 更新予定のgroupデータ。

    Raises:
        HTTPException: group名が空または別groupと重複する場合。
    """
    _group_master.validate_update(
        db,
        object_id=group_id_to_update,
        name=group_in.name,
    )


def create_group_with_validation(
    db: Session, *, group_in: schemas.GroupCreate
) -> models.Group:
    """groupを検証して作成し、service所有のtransactionでcommitする。

    Args:
        db: DB session。
        group_in: 作成するgroupデータ。

    Returns:
        作成後のgroup model。

    Raises:
        HTTPException: group名validationに失敗した場合。
        ApplicationError: DB integrity conflictが発生した場合。
    """
    return _group_master.create(db, obj_in=group_in, name=group_in.name)


def update_group_with_validation(
    db: Session, *, group_id: int, group_in: schemas.GroupUpdate
) -> models.Group:
    """既存groupを検証して1 transactionで更新する。

    Args:
        db: DB session。
        group_id: 更新対象group ID。
        group_in: 更新内容。

    Returns:
        更新後のgroup model。

    Raises:
        HTTPException: 対象不在またはgroup名validationに失敗した場合。
        ApplicationError: DB integrity conflictが発生した場合。
    """
    return _group_master.update(
        db,
        object_id=group_id,
        obj_in=group_in,
        name=group_in.name,
    )


def delete_group(db: Session, *, group_id: int) -> models.Group:
    """未使用groupを削除する。

    Args:
        db: DB session。
        group_id: 削除対象group ID。

    Returns:
        削除したgroup model。

    Raises:
        HTTPException: 対象groupが存在しない場合。
        ApplicationError: DB参照制約等により削除できない場合。
    """
    return _group_master.delete(db, object_id=group_id)
