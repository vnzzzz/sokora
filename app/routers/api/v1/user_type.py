"""
社員種別APIエンドポイント
=====================

社員種別の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud.user_type import user_type
from app.db.session import get_db
from app.schemas.user_type import UserType, UserTypeCreate, UserTypeList, UserTypeUpdate
from app.services import user_type_service

router = APIRouter(tags=["UserTypes"])


@router.get("", response_model=UserTypeList)
def get_user_types(db: Session = Depends(get_db)) -> Any:
    """社員種別一覧を表示順、次に名前順で返します。"""
    user_types = user_type.get_multi(db=db)
    return {"user_types": user_types}


@router.post("", response_model=UserType)
def create_user_type(
    *, db: Session = Depends(get_db), user_type_in: UserTypeCreate
) -> Any:
    """入力を検証して社員種別を作成し、作成後の社員種別を返します。"""
    return user_type_service.create_user_type_with_validation(
        db=db, user_type_in=user_type_in
    )


@router.put("/{user_type_id}", response_model=UserType)
def update_user_type(
    *,
    db: Session = Depends(get_db),
    user_type_id: int,
    user_type_in: UserTypeUpdate,
) -> Any:
    """指定IDの社員種別を検証して更新し、更新後の社員種別を返します。"""
    return user_type_service.update_user_type_with_validation(
        db=db, user_type_id=user_type_id, user_type_in=user_type_in
    )


@router.delete("/{user_type_id}")
def delete_user_type(*, db: Session = Depends(get_db), user_type_id: int) -> Any:
    """指定IDの未使用社員種別を削除し、成功時は204を返します。"""
    user_type_service.delete_user_type(db=db, user_type_id=user_type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
