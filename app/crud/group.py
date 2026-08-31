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
        """グループ名で1件取得し、存在しない場合は ``None`` を返します。"""
        return db.query(Group).filter(Group.name == name).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Group]:
        """``order``、次に名前の順でグループ一覧を取得します。"""
        return (
            db.query(Group)
            .order_by(Group.order.nullslast(), Group.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def remove(self, db: Session, *, id: int) -> Group:
        """未使用のグループを削除対象としてflushし、削除対象を返します。

        ユーザーから参照されている場合はHTTP 400を送出します。commit/rollbackは
        呼び出し側serviceが所有します。
        """
        db_obj = self.get_or_404(db, id)

        # この事前チェックは利用者向けエラーのために行う。
        # 並行writeとの競合時はDBのFK制約が最終的な参照整合性を保証する。
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
