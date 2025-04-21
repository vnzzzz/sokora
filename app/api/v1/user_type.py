"""
社員種別APIエンドポイント
=====================

社員種別の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user_type import user_type
from ...schemas.user_type import UserType, UserTypeCreate, UserTypeList, UserTypeUpdate

router = APIRouter(tags=["UserTypes"])


@router.get("/", response_model=UserTypeList)
def get_user_types(db: Session = Depends(get_db)) -> Any:
    """
    全ての社員種別を取得します。名前順でソートされます。
    """
    user_types = db.query(user_type.model).order_by(user_type.model.name).all()
    return {"user_types": user_types}


@router.post("/", response_model=UserType)
def create_user_type(
    *, db: Session = Depends(get_db), user_type_in: UserTypeCreate
) -> Any:
    """
    新しい社員種別を作成します。
    """
    if not user_type_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="社員種別名を入力してください",
        )
    
    existing_user_type = user_type.get_by_name(db, name=user_type_in.name)
    if existing_user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この社員種別は既に存在します",
        )
    
    return user_type.create(db=db, obj_in=user_type_in)


@router.put("/{user_type_id}", response_model=UserType)
def update_user_type(
    *,
    db: Session = Depends(get_db),
    user_type_id: int,
    user_type_in: UserTypeUpdate,
) -> Any:
    """
    社員種別を更新します。
    """
    user_type_obj = user_type.get_by_id(db=db, user_type_id=user_type_id)
    if not user_type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="社員種別が見つかりません"
        )
    
    # 名前を変更する場合は重複チェック
    if user_type_in.name and user_type_in.name != user_type_obj.name:
        existing = user_type.get_by_name(db, name=user_type_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この社員種別名は既に使用されています",
            )
    
    return user_type.update(db=db, db_obj=user_type_obj, obj_in=user_type_in)


@router.delete("/{user_type_id}")
def delete_user_type(*, db: Session = Depends(get_db), user_type_id: int) -> Any:
    """
    社員種別を削除します。
    """
    user_type_obj = user_type.get_by_id(db=db, user_type_id=user_type_id)
    if not user_type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="社員種別が見つかりません"
        )
    
    # 社員種別が使用されているかチェック
    from ...models.user import User
    user_count = db.query(User).filter(User.user_type_id == user_type_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"この社員種別は{user_count}人のユーザーに割り当てられているため削除できません"
        )

    user_type.remove(db=db, id=user_type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 