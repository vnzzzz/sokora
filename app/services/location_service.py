"""勤怠種別関連のvalidationとtransaction境界を提供するservice。"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.transaction import transaction


def validate_location_creation(
    db: Session, *, location_in: schemas.location.LocationCreate
) -> None:
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    if not location_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="勤怠種別名を入力してください",
        )
    existing_location = crud.location.get_by_name(db, name=location_in.name)
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この勤怠種別名は既に存在します",
        )


def validate_location_update(
    db: Session,
    *,
    location_id_to_update: int,
    location_in: schemas.location.LocationUpdate,
) -> None:
    """更新対象自身を除外して勤怠種別名の必須・重複条件を検証します。"""
    if not location_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="勤怠種別名を入力してください",
        )
    existing_location = crud.location.get_by_name(db, name=location_in.name)
    if existing_location and existing_location.id != location_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この勤怠種別名は既に使用されています",
        )


def create_location_with_validation(
    db: Session, *, location_in: schemas.location.LocationCreate
) -> models.Location:
    """勤怠種別を検証して作成し、service所有のtransactionでcommitします。"""
    with transaction(db, integrity_detail="この勤怠種別名は既に存在します"):
        validate_location_creation(db, location_in=location_in)
        created = crud.location.create(db, obj_in=location_in)
    return created


def update_location_with_validation(
    db: Session, *, location_id: int, location_in: schemas.location.LocationUpdate
) -> models.Location:
    """既存勤怠種別を検証して更新し、1 transactionでcommitします。"""
    with transaction(db, integrity_detail="この勤怠種別名は既に使用されています"):
        db_location = crud.location.get_or_404(db, id=location_id)
        validate_location_update(
            db, location_id_to_update=location_id, location_in=location_in
        )
        updated = crud.location.update(db, db_obj=db_location, obj_in=location_in)
    return updated


def delete_location(db: Session, *, location_id: int) -> models.Location:
    """未使用勤怠種別を削除し、参照競合はDB制約エラーとして扱います。"""
    with transaction(db, integrity_detail="利用中の勤怠種別は削除できません"):
        deleted = crud.location.remove(db, id=location_id)
    return deleted
