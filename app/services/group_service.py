"""グループ関連のvalidationとtransaction境界を提供するservice。"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.transaction import transaction


def validate_group_creation(db: Session, *, group_in: schemas.GroupCreate) -> None:
    """作成前に必須名と名前重複を検証し、違反時はHTTP 400を送出します。"""
    if not group_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="グループ名を入力してください",
        )
    existing_group = crud.group.get_by_name(db, name=group_in.name)
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このグループ名は既に存在します",
        )


def validate_group_update(
    db: Session, *, group_id_to_update: int, group_in: schemas.GroupUpdate
) -> None:
    """更新対象自身を除外してグループ名の必須・重複条件を検証します。"""
    if not group_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="グループ名を入力してください",
        )
    existing_group = crud.group.get_by_name(db, name=group_in.name)
    if existing_group and existing_group.id != group_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このグループ名は既に使用されています",
        )


def create_group_with_validation(
    db: Session, *, group_in: schemas.GroupCreate
) -> models.Group:
    """グループを検証して作成し、service所有のtransactionでcommitします。"""
    with transaction(db, integrity_detail="このグループ名は既に存在します"):
        validate_group_creation(db, group_in=group_in)
        created = crud.group.create(db, obj_in=group_in)
    return created


def update_group_with_validation(
    db: Session, *, group_id: int, group_in: schemas.GroupUpdate
) -> models.Group:
    """既存グループを検証して更新し、1 transactionでcommitします。"""
    with transaction(db, integrity_detail="このグループ名は既に使用されています"):
        db_group = crud.group.get_or_404(db, id=group_id)
        validate_group_update(db, group_id_to_update=group_id, group_in=group_in)
        updated = crud.group.update(db, db_obj=db_group, obj_in=group_in)
    return updated


def delete_group(db: Session, *, group_id: int) -> models.Group:
    """未使用グループを削除し、参照競合はDB制約エラーとして扱います。"""
    with transaction(db, integrity_detail="利用中のグループは削除できません"):
        deleted = crud.group.remove(db, id=group_id)
    return deleted
