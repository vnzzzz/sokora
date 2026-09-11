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
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    _group_master.validate_creation(db, name=group_in.name)


def validate_group_update(
    db: Session, *, group_id_to_update: int, group_in: schemas.GroupUpdate
) -> None:
    """更新対象自身を除外してグループ名の必須・重複条件を検証します。"""
    _group_master.validate_update(
        db,
        object_id=group_id_to_update,
        name=group_in.name,
    )


def create_group_with_validation(
    db: Session, *, group_in: schemas.GroupCreate
) -> models.Group:
    """グループを検証して作成し、service所有のtransactionでcommitします。"""
    return _group_master.create(db, obj_in=group_in, name=group_in.name)


def update_group_with_validation(
    db: Session, *, group_id: int, group_in: schemas.GroupUpdate
) -> models.Group:
    """既存グループを検証して更新し、1 transactionでcommitします。"""
    return _group_master.update(
        db,
        object_id=group_id,
        obj_in=group_in,
        name=group_in.name,
    )


def delete_group(db: Session, *, group_id: int) -> models.Group:
    """未使用グループを削除し、参照競合はDB制約エラーとして扱います。"""
    return _group_master.delete(db, object_id=group_id)
