"""ユーザー関連のvalidationとtransaction境界を提供するservice。"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.transaction import transaction


def get_user_by_username(db: Session, *, username: str) -> Optional[models.User]:
    """ユーザー名で1件取得し、存在しない場合は ``None`` を返します。"""
    return db.query(models.User).filter(models.User.username == username).first()


def validate_dependencies(db: Session, *, group_id: int, user_type_id: int) -> None:
    """指定されたグループと社員種別が存在することを検証します。"""
    group = crud.group.get(db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"指定されたグループID({group_id})は存在しません。",
        )
    user_type = crud.user_type.get(db, id=user_type_id)
    if not user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"指定された社員種別ID({user_type_id})は存在しません。",
        )


def validate_user_creation(db: Session, *, user_in: schemas.UserCreate) -> None:
    """ユーザーIDとユーザー名が未使用であることを検証します。"""
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
    """更新対象自身を除外してユーザー名の重複を検証します。"""
    existing_user_by_name = get_user_by_username(db, username=user_in.username)
    if existing_user_by_name and existing_user_by_name.id != user_id_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ユーザー名 '{user_in.username}' は既に使用されています。",
        )


def create_user_with_validation(
    db: Session, *, user_in: schemas.UserCreate
) -> models.User:
    """関連IDと一意性を検証してユーザーを1 transactionで作成します。"""
    try:
        group_id_int = int(user_in.group_id)
        user_type_id_int = int(user_in.user_type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="グループIDまたは社員種別IDが無効な形式です。",
        )

    with transaction(
        db, integrity_detail="ユーザーの一意性または参照整合性に違反しました"
    ):
        validate_dependencies(db, group_id=group_id_int, user_type_id=user_type_id_int)
        validate_user_creation(db, user_in=user_in)
        user_create_validated = user_in.model_copy(
            update={"group_id": group_id_int, "user_type_id": user_type_id_int}
        )
        created = crud.user.create(db, obj_in=user_create_validated)
    return created


def update_user_with_validation(
    db: Session, *, user_id: str, user_in: schemas.UserUpdate
) -> models.User:
    """既存ユーザーと依存先を検証し、1 transactionで更新します。"""
    with transaction(
        db, integrity_detail="ユーザーの一意性または参照整合性に違反しました"
    ):
        db_user = crud.user.get_or_404(db, id=user_id)
        validate_dependencies(
            db, group_id=user_in.group_id, user_type_id=user_in.user_type_id
        )
        validate_user_update(db, user_id_to_update=user_id, user_in=user_in)
        updated = crud.user.update(db, db_obj=db_user, obj_in=user_in)
    return updated


def delete_user(db: Session, *, user_id: str) -> models.User:
    """ユーザーと関連勤怠を同一transactionで削除し、削除したユーザーを返します。"""
    with transaction(db, integrity_detail="ユーザー削除時の参照整合性に違反しました"):
        crud.user.get_or_404(db, id=user_id)

        # FK enforcement下でuserだけが先に消えないよう、依存する勤怠を先にstageする。
        # attendance削除とuser削除はこのservice transactionでまとめて確定またはrollbackされる。
        db.query(models.Attendance).filter(models.Attendance.user_id == user_id).delete(
            synchronize_session=False
        )
        db.flush()
        deleted = crud.user.remove(db, id=user_id)
    return deleted
