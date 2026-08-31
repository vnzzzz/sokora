"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud.user import user
from app.db.session import get_db
from app.schemas.user import User, UserCreate, UserList, UserUpdate
from app.services import user_service

router = APIRouter(tags=["Users"])


@router.get("", response_model=UserList)
def get_users(db: Session = Depends(get_db)) -> Any:
    """登録済みユーザー一覧を返します。"""
    users_data = user.get_all_users(db)
    users_list = []
    for _user_name, user_id_str, _user_type_id in users_data:
        user_obj = user.get(db, id=user_id_str)
        if user_obj:
            users_list.append(user_obj)
    return {"users": users_list}


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)) -> Any:
    """指定IDのユーザーを返し、存在しない場合は404を返します。"""
    return user.get_or_404(db, id=user_id)


@router.post("", response_model=User)
async def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    """関連IDと一意性を検証してユーザーを作成し、作成後のユーザーを返します。"""
    return user_service.create_user_with_validation(db=db, user_in=user_in)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
) -> Any:
    """指定IDのユーザーを検証して更新し、更新後のユーザーを返します。"""
    return user_service.update_user_with_validation(
        db=db, user_id=user_id, user_in=user_in
    )


@router.delete("/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)) -> Any:
    """ユーザーと関連勤怠を同一transactionで削除し、成功時は204を返します。"""
    user_service.delete_user(db=db, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
