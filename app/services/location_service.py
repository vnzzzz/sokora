"""
勤務場所関連のビジネスロジックを提供するサービス層モジュール。
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas


def validate_location_creation(db: Session, *, location_in: schemas.location.LocationCreate) -> None:
    """勤務場所新規作成時のバリデーション（名前の重複チェック）を行います。"""
    if not location_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="勤務場所名を入力してください",
        )
    existing_location = crud.location.get_by_name(db, name=location_in.name)
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この勤務場所名は既に存在します",
        )


def validate_location_update(
    db: Session, *, location_id_to_update: int, location_in: schemas.location.LocationUpdate
) -> None:
    """勤務場所更新時のバリデーション（名前の重複チェック）を行います。"""
    if not location_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="勤務場所名を入力してください",
        )
    existing_location = crud.location.get_by_name(db, name=location_in.name)
    # 取得した勤務場所が、更新対象の勤務場所自身でなければ重複エラー
    if existing_location and existing_location.id != location_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この勤務場所名は既に使用されています",
        )


def create_location_with_validation(
    db: Session, *, location_in: schemas.location.LocationCreate
) -> models.Location:
    """
    バリデーションを実行してから勤務場所を新規作成します。
    """
    validate_location_creation(db, location_in=location_in)
    return crud.location.create(db, obj_in=location_in)


def update_location_with_validation(
    db: Session, *, location_id: int, location_in: schemas.location.LocationUpdate
) -> models.Location:
    """
    バリデーションを実行してから勤務場所情報を更新します。
    """
    # まず更新対象が存在するか確認 (なければ404)
    db_location = crud.location.get_or_404(db, id=location_id)

    # 更新バリデーションを実行
    validate_location_update(db, location_id_to_update=location_id, location_in=location_in)

    # バリデーションが通れば更新を実行
    return crud.location.update(db, db_obj=db_location, obj_in=location_in) 