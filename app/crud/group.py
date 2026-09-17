"""
グループCRUD操作
==============

グループモデルに対するCRUD操作を提供します。
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate

from .base import CRUDBase


class CRUDGroup(CRUDBase[Group, GroupCreate, GroupUpdate]):
    """グループ固有の検索・並び順・参照チェックを追加したCRUD操作。"""

    def get_by_name(self, db: Session, name: str) -> Optional[Group]:
        """グループ名で1件取得する。

        Args:
            db: DB session。
            name: 検索するグループ名。

        Returns:
            一致するgroup。存在しない場合は`None`。
        """
        return db.query(Group).filter(Group.name == name).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Group]:
        """表示順・名前順でgroup一覧を取得する。

        Args:
            db: DB session。
            skip: 先頭からskipする件数。
            limit: 最大取得件数。

        Returns:
            pagination適用済みのgroup list。
        """
        return (
            db.query(Group)
            .order_by(Group.order.nullslast(), Group.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session) -> List[Group]:
        """全groupを表示順・名前順で取得する。

        Args:
            db: DB session。

        Returns:
            全groupのlist。
        """
        return db.query(Group).order_by(Group.order.nullslast(), Group.name).all()

    def remove(self, db: Session, *, id: int) -> Group:
        """未使用groupを削除対象としてflushする。

        userから参照されている場合は利用者向け400を返すため事前チェックする。並行writeとの
        競合時はDB FK制約が最終的な参照整合性を保証する。commit/rollbackはserviceが所有する。

        Args:
            db: DB session。
            id: 削除対象group ID。

        Returns:
            削除stage済みのgroup model。

        Raises:
            HTTPException: 対象不在、またはuserから参照されている場合。
        """
        db_obj = self.get_or_404(db, id)

        user_count = db.query(User).filter(User.group_id == id).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"このグループは{user_count}人のユーザーに割り当てられているため削除できません",
            )

        db.delete(db_obj)
        db.flush()
        return db_obj


group = CRUDGroup(Group)
