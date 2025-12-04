"""
社員種別関連のビジネスロジックを提供するサービス層モジュール。
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas


def validate_user_type_creation(db: Session, *, user_type_in: schemas.user_type.UserTypeCreate) -> None:
    """社員種別新規作成時のバリデーション（名前の重複チェック）を行います。"""
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
    db: Session, *, user_type_id_to_update: int, user_type_in: schemas.user_type.UserTypeUpdate
) -> None:
    """社員種別更新時のバリデーション（名前の重複チェック）を行います。"""
    if not user_type_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="社員種別名を入力してください",
        )
    existing_user_type = crud.user_type.get_by_name(db, name=user_type_in.name)
    # 取得した社員種別が、更新対象の社員種別自身でなければ重複エラー
    if existing_user_type and existing_user_type.id != user_type_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この社員種別名は既に使用されています",
        )


def create_user_type_with_validation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> models.UserType:
    """
    バリデーションを実行してから社員種別を新規作成します。
    """
    validate_user_type_creation(db, user_type_in=user_type_in)
    return crud.user_type.create(db, obj_in=user_type_in)


def update_user_type_with_validation(
    db: Session, *, user_type_id: int, user_type_in: schemas.user_type.UserTypeUpdate
) -> models.UserType:
    """
    バリデーションを実行してから社員種別情報を更新します。
    """
    # まず更新対象が存在するか確認 (なければ404)
    db_user_type = crud.user_type.get_or_404(db, id=user_type_id)

    # 更新バリデーションを実行
    validate_user_type_update(db, user_type_id_to_update=user_type_id, user_type_in=user_type_in)

    # バリデーションが通れば更新を実行
    return crud.user_type.update(db, db_obj=db_user_type, obj_in=user_type_in) 