"""社員種別関連のvalidationとtransaction境界を提供するservice。"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.transaction import transaction


def validate_user_type_creation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> None:
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    if not user_type_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="社員種別名を入力してください",
        )
    existing_user_type = crud.user_type.get_by_name(db, name=user_type_in.name)
    if existing_user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この社員種別名は既に存在します",
        )


def validate_user_type_update(
    db: Session,
    *,
    user_type_id_to_update: int,
    user_type_in: schemas.user_type.UserTypeUpdate,
) -> None:
    """更新対象自身を除外して社員種別名の必須・重複条件を検証します。"""
    if not user_type_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="社員種別名を入力してください",
        )
    existing_user_type = crud.user_type.get_by_name(db, name=user_type_in.name)
    if existing_user_type and existing_user_type.id != user_type_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この社員種別名は既に使用されています",
        )


def create_user_type_with_validation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> models.UserType:
    """社員種別を検証して作成し、service所有のtransactionでcommitします。"""
    with transaction(db, integrity_detail="この社員種別名は既に存在します"):
        validate_user_type_creation(db, user_type_in=user_type_in)
        created = crud.user_type.create(db, obj_in=user_type_in)
    return created


def update_user_type_with_validation(
    db: Session, *, user_type_id: int, user_type_in: schemas.user_type.UserTypeUpdate
) -> models.UserType:
    """既存社員種別を検証して更新し、1 transactionでcommitします。"""
    with transaction(db, integrity_detail="この社員種別名は既に使用されています"):
        db_user_type = crud.user_type.get_or_404(db, id=user_type_id)
        validate_user_type_update(
            db, user_type_id_to_update=user_type_id, user_type_in=user_type_in
        )
        updated = crud.user_type.update(db, db_obj=db_user_type, obj_in=user_type_in)
    return updated


def delete_user_type(db: Session, *, user_type_id: int) -> models.UserType:
    """未使用社員種別を削除し、参照競合はDB制約エラーとして扱います。"""
    with transaction(db, integrity_detail="利用中の社員種別は削除できません"):
        deleted = crud.user_type.remove(db, id=user_type_id)
    return deleted
