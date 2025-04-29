# TODO: Implement user service logic 

"""
ユーザー関連のビジネスロジックを提供するサービス層モジュール。
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas


def get_user_by_username(db: Session, *, username: str) -> Optional[models.User]:
    """指定されたユーザー名を持つユーザーを取得します。"""
    return db.query(models.User).filter(models.User.username == username).first()


def validate_dependencies(db: Session, *, group_id: int, user_type_id: int) -> None:
    """ユーザー作成・更新時の依存関係（グループ、社員種別）の存在を検証します。"""
    group = crud.group.get(db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'指定されたグループID({group_id})は存在しません。',
        )
    user_type = crud.user_type.get(db, id=user_type_id)
    if not user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'指定された社員種別ID({user_type_id})は存在しません。',
        )


def validate_user_creation(db: Session, *, user_in: schemas.UserCreate) -> None:
    """ユーザー新規作成時のバリデーション（IDとユーザー名の重複チェック）を行います。"""
    existing_user_by_id = crud.user.get(db, id=user_in.id)
    if existing_user_by_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ユーザーID '{user_in.id}' は既に使用されています。",
        )
    existing_user_by_name = get_user_by_username(db, username=user_in.username)
    if existing_user_by_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ユーザー名 '{user_in.username}' は既に使用されています。",
        )


def validate_user_update(
    db: Session, *, user_id_to_update: str, user_in: schemas.UserUpdate
) -> None:
    """ユーザー更新時のバリデーション（ユーザー名の重複チェック）を行います。"""
    existing_user_by_name = get_user_by_username(db, username=user_in.username)
    if existing_user_by_name and existing_user_by_name.id != user_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ユーザー名 '{user_in.username}' は既に使用されています。",
        )


def create_user_with_validation(
    db: Session, *, user_in: schemas.UserCreate
) -> models.User:
    """
    バリデーションを実行してからユーザーを新規作成します。
    """
    # group_id と user_type_id を int に変換 (スキーマで str|int 許容のため)
    try:
        group_id_int = int(user_in.group_id)
        user_type_id_int = int(user_in.user_type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='グループIDまたは社員種別IDが無効な形式です。',
        )

    validate_dependencies(db, group_id=group_id_int, user_type_id=user_type_id_int)
    validate_user_creation(db, user_in=user_in)

    # int に変換した値でスキーマを更新して CRUD に渡す (より厳密にするため)
    user_create_validated = user_in.model_copy(
        update={'group_id': group_id_int, 'user_type_id': user_type_id_int}
    )

    return crud.user.create(db, obj_in=user_create_validated)


def update_user_with_validation(
    db: Session, *, user_id: str, user_in: schemas.UserUpdate
) -> models.User:
    """
    バリデーションを実行してからユーザー情報を更新します。
    """
    db_user = crud.user.get_or_404(db, id=user_id)

    validate_dependencies(db, group_id=user_in.group_id, user_type_id=user_in.user_type_id)
    validate_user_update(db, user_id_to_update=user_id, user_in=user_in)

    return crud.user.update(db, db_obj=db_user, obj_in=user_in) 