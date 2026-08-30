"""
グループAPIエンドポイント
=====================

グループの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.group import group
from app.db.session import get_db
from app.models.user import User
from app.schemas.group import Group, GroupCreate, GroupList, GroupUpdate

router = APIRouter(tags=["Groups"])


@router.get("", response_model=GroupList)
def get_groups(db: Session = Depends(get_db)) -> Any:
    """
    全てのグループを取得します。名前順でソートされます。
    """
    groups = db.query(group.model).order_by(group.model.name).all()
    return {"groups": groups}


@router.post("", response_model=Group)
def create_group(
    *, db: Session = Depends(get_db), group_in: GroupCreate
) -> Any:
    """
    新しいグループを作成します。
    """
    if not group_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="グループ名を入力してください",
        )
    
    existing_group = group.get_by_name(db, name=group_in.name)
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このグループは既に存在します",
        )
    
    return group.create(db=db, obj_in=group_in)


@router.put("/{group_id}", response_model=Group)
def update_group(
    *,
    db: Session = Depends(get_db),
    group_id: int,
    group_in: GroupUpdate,
) -> Any:
    """
    グループを更新します。
    """
    group_obj = group.get_or_404(db=db, id=group_id)
    
    # 新しい名前が指定され、かつ現在の名前と異なる場合に重複チェックを行います。
    if group_in.name and group_in.name != group_obj.name:
        existing = group.get_by_name(db, name=group_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このグループ名は既に使用されています",
            )
    
    return group.update(db=db, db_obj=group_obj, obj_in=group_in)


@router.delete("/{group_id}")
def delete_group(*, db: Session = Depends(get_db), group_id: int) -> Any:
    """
    グループを削除します。
    """
    group_obj = group.get_or_404(db=db, id=group_id)
    
    group.remove(db=db, id=group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 