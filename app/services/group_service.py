# TODO: Implement group service logic 
"""
グループ関連のビジネスロジックを提供するサービス層モジュール。
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas


def validate_group_creation(db: Session, *, group_in: schemas.GroupCreate) -> None:
    """グループ新規作成時のバリデーション（名前の重複チェック）を行います。"""
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
    """グループ更新時のバリデーション（名前の重複チェック）を行います。"""
    if not group_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="グループ名を入力してください",
        )
    existing_group = crud.group.get_by_name(db, name=group_in.name)
    # 取得したグループが、更新対象のグループ自身でなければ重複エラー
    if existing_group and existing_group.id != group_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このグループ名は既に使用されています",
        )


def create_group_with_validation(
    db: Session, *, group_in: schemas.GroupCreate
) -> models.Group:
    """
    バリデーションを実行してからグループを新規作成します。
    """
    validate_group_creation(db, group_in=group_in)
    return crud.group.create(db, obj_in=group_in)


def update_group_with_validation(
    db: Session, *, group_id: int, group_in: schemas.GroupUpdate
) -> models.Group:
    """
    バリデーションを実行してからグループ情報を更新します。
    """
    # まず更新対象が存在するか確認 (なければ404)
    db_group = crud.group.get_or_404(db, id=group_id)
    
    # 更新バリデーションを実行
    validate_group_update(db, group_id_to_update=group_id, group_in=group_in)

    # バリデーションが通れば更新を実行
    return crud.group.update(db, db_obj=db_group, obj_in=group_in) 