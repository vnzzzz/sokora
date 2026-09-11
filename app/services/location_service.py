"""勤怠種別関連のvalidationとtransaction境界を提供するservice。"""

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.named_master_service import NamedMasterMessages, NamedMasterService

_location_master = NamedMasterService[
    models.Location,
    schemas.location.LocationCreate,
    schemas.location.LocationUpdate,
](
    crud=crud.location,
    get_by_name=lambda db, name: crud.location.get_by_name(db, name=name),
    get_id=lambda location: int(location.id),
    messages=NamedMasterMessages(
        required_name="勤怠種別名を入力してください",
        duplicate_create="この勤怠種別名は既に存在します",
        duplicate_update="この勤怠種別名は既に使用されています",
        delete_integrity="利用中の勤怠種別は削除できません",
    ),
)


def validate_location_creation(
    db: Session, *, location_in: schemas.location.LocationCreate
) -> None:
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    _location_master.validate_creation(db, name=location_in.name)


def validate_location_update(
    db: Session,
    *,
    location_id_to_update: int,
    location_in: schemas.location.LocationUpdate,
) -> None:
    """更新対象自身を除外して勤怠種別名の必須・重複条件を検証します。"""
    _location_master.validate_update(
        db,
        object_id=location_id_to_update,
        name=location_in.name,
    )


def create_location_with_validation(
    db: Session, *, location_in: schemas.location.LocationCreate
) -> models.Location:
    """勤怠種別を検証して作成し、service所有のtransactionでcommitします。"""
    return _location_master.create(db, obj_in=location_in, name=location_in.name)


def update_location_with_validation(
    db: Session, *, location_id: int, location_in: schemas.location.LocationUpdate
) -> models.Location:
    """既存勤怠種別を検証して更新し、1 transactionでcommitします。"""
    return _location_master.update(
        db,
        object_id=location_id,
        obj_in=location_in,
        name=location_in.name,
    )


def delete_location(db: Session, *, location_id: int) -> models.Location:
    """未使用勤怠種別を削除し、参照競合はDB制約エラーとして扱います。"""
    return _location_master.delete(db, object_id=location_id)
