"""社員種別関連のvalidationとtransaction境界を提供するservice。"""

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.named_master_service import NamedMasterMessages, NamedMasterService

_user_type_master = NamedMasterService[
    models.UserType,
    schemas.user_type.UserTypeCreate,
    schemas.user_type.UserTypeUpdate,
](
    crud=crud.user_type,
    get_by_name=lambda db, name: crud.user_type.get_by_name(db, name=name),
    get_id=lambda user_type: int(user_type.id),
    messages=NamedMasterMessages(
        required_name="社員種別名を入力してください",
        duplicate_create="この社員種別名は既に存在します",
        duplicate_update="この社員種別名は既に使用されています",
        delete_integrity="利用中の社員種別は削除できません",
    ),
)


def validate_user_type_creation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> None:
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    _user_type_master.validate_creation(db, name=user_type_in.name)


def validate_user_type_update(
    db: Session,
    *,
    user_type_id_to_update: int,
    user_type_in: schemas.user_type.UserTypeUpdate,
) -> None:
    """更新対象自身を除外して社員種別名の必須・重複条件を検証します。"""
    _user_type_master.validate_update(
        db,
        object_id=user_type_id_to_update,
        name=user_type_in.name,
    )


def create_user_type_with_validation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> models.UserType:
    """社員種別を検証して作成し、service所有のtransactionでcommitします。"""
    return _user_type_master.create(db, obj_in=user_type_in, name=user_type_in.name)


def update_user_type_with_validation(
    db: Session, *, user_type_id: int, user_type_in: schemas.user_type.UserTypeUpdate
) -> models.UserType:
    """既存社員種別を検証して更新し、1 transactionでcommitします。"""
    return _user_type_master.update(
        db,
        object_id=user_type_id,
        obj_in=user_type_in,
        name=user_type_in.name,
    )


def delete_user_type(db: Session, *, user_type_id: int) -> models.UserType:
    """未使用社員種別を削除し、参照競合はDB制約エラーとして扱います。"""
    return _user_type_master.delete(db, object_id=user_type_id)
