"""
社員種別APIエンドポイント
=====================

社員種別の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.user_type import user_type
from app.db.session import get_db
from app.schemas.user_type import UserType, UserTypeCreate, UserTypeList, UserTypeUpdate

# サービス層をインポート
from app.services import user_type_service

router = APIRouter(tags=["UserTypes"])


@router.get("", response_model=UserTypeList)
def get_user_types(db: Session = Depends(get_db)) -> Any:
    """
    全ての社員種別を取得します。表示順（order）順、次に名前順でソートされます。
    """
    user_types = user_type.get_multi(db=db)
    return {"user_types": user_types}


@router.post("", response_model=UserType)
def create_user_type(
    *, db: Session = Depends(get_db), user_type_in: UserTypeCreate
) -> Any:
    """
    新しい社員種別を作成します。
    サービス層でバリデーションを実行します。
    """
    # バリデーションと作成をサービス層に委譲
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
    """
    社員種別を更新します。
    サービス層でバリデーションを実行します。
    """
    # バリデーションと更新をサービス層に委譲
    return user_type_service.update_user_type_with_validation(
        db=db, user_type_id=user_type_id, user_type_in=user_type_in
    )


@router.delete("/{user_type_id}")
def delete_user_type(*, db: Session = Depends(get_db), user_type_id: int) -> Any:
    """
    社員種別を削除します。
    """
    user_type_obj = user_type.get_or_404(db=db, id=user_type_id)
    
    # 削除しようとしている社員種別が現在ユーザーに割り当てられていないか確認します。
    # user_count = db.query(User).filter(User.user_type_id == user_type_id).count()
    # if user_count > 0:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"この社員種別は{user_count}人のユーザーに割り当てられているため削除できません"
    #     )
    # ↑ このチェックは crud.user_type.remove 内に移動

    user_type.remove(db=db, id=user_type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 