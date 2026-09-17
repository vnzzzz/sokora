"""
グループAPIエンドポイント
=====================

グループの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud.group import group
from app.db.session import get_db
from app.schemas.group import Group, GroupCreate, GroupList, GroupUpdate
from app.services import group_service

router = APIRouter(tags=["Groups"])


@router.get("", response_model=GroupList)
def get_groups(db: Session = Depends(get_db)) -> Any:
    """グループ一覧を表示順、次に名前順で返す。

    Args:
        db: DB session。

    Returns:
        `groups`にグループ一覧を格納したmapping。
    """
    groups = group.list_all(db=db)
    return {"groups": groups}


@router.post("", response_model=Group)
def create_group(*, db: Session = Depends(get_db), group_in: GroupCreate) -> Any:
    """入力を検証してグループを作成する。

    Args:
        db: DB session。
        group_in: 作成するグループデータ。

    Returns:
        作成後のグループ。

    Raises:
        HTTPException: 名前が不正または重複する場合。
    """
    return group_service.create_group_with_validation(db=db, group_in=group_in)


@router.put("/{group_id}", response_model=Group)
def update_group(
    *,
    db: Session = Depends(get_db),
    group_id: int,
    group_in: GroupUpdate,
) -> Any:
    """指定IDのグループを検証して更新する。

    Args:
        db: DB session。
        group_id: 更新対象のグループID。
        group_in: 更新内容。

    Returns:
        更新後のグループ。

    Raises:
        HTTPException: 対象が存在しない、または名前が不正/重複する場合。
    """
    return group_service.update_group_with_validation(
        db=db, group_id=group_id, group_in=group_in
    )


@router.delete("/{group_id}")
def delete_group(*, db: Session = Depends(get_db), group_id: int) -> Any:
    """指定IDの未使用グループを削除する。

    Args:
        db: DB session。
        group_id: 削除対象のグループID。

    Returns:
        bodyなしの204 response。

    Raises:
        HTTPException: 対象が存在しない、または参照中で削除できない場合。
    """
    group_service.delete_group(db=db, group_id=group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
