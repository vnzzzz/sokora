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

# サービス層をインポート
from app.services import group_service

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
    サービス層でバリデーションを実行します。
    """
    # バリデーションと作成をサービス層に委譲
    return group_service.create_group_with_validation(db=db, group_in=group_in)


@router.put("/{group_id}", response_model=Group)
def update_group(
    *,
    db: Session = Depends(get_db),
    group_id: int,
    group_in: GroupUpdate,
) -> Any:
    """
    グループを更新します。
    サービス層でバリデーションを実行します。
    """
    # バリデーションと更新をサービス層に委譲
    return group_service.update_group_with_validation(
        db=db, group_id=group_id, group_in=group_in
    )


@router.delete("/{group_id}")
def delete_group(*, db: Session = Depends(get_db), group_id: int) -> Any:
    """
    グループを削除します。
    """
    group_obj = group.get_or_404(db=db, id=group_id)
    
    group.remove(db=db, id=group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 