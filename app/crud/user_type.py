"""
社員種別CRUD操作
==============

社員種別モデルに対するCRUD操作を提供します。
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate, UserTypeUpdate

from .base import CRUDBase


class CRUDUserType(CRUDBase[UserType, UserTypeCreate, UserTypeUpdate]):
    """社員種別固有の検索・並び順・参照チェックを追加したCRUD操作。"""

    def get_by_name(self, db: Session, name: str) -> Optional[UserType]:
        """社員種別名で1件取得する。

        Args:
            db: DB session。
            name: 検索する社員種別名。

        Returns:
            一致する社員種別。存在しない場合は`None`。
        """
        return db.query(UserType).filter(UserType.name == name).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserType]:
        """表示順・名前順で社員種別一覧を取得する。

        Args:
            db: DB session。
            skip: 先頭からskipする件数。
            limit: 最大取得件数。

        Returns:
            pagination適用済みの社員種別list。
        """
        return (
            db.query(UserType)
            .order_by(UserType.order.nullslast(), UserType.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session) -> List[UserType]:
        """全社員種別を表示順・名前順で取得する。

        Args:
            db: DB session。

        Returns:
            全社員種別のlist。
        """
        query = db.query(UserType)
        return query.order_by(UserType.order.nullslast(), UserType.name).all()

    def remove(self, db: Session, *, id: int) -> UserType:
        """未使用の社員種別を削除対象としてflushする。

        userから参照されている場合は利用者向け400を返すため事前チェックする。並行writeとの
        競合時はDB FK制約が最終的な参照整合性を保証する。commit/rollbackはserviceが所有する。

        Args:
            db: DB session。
            id: 削除対象の社員種別ID。

        Returns:
            削除stage済みの社員種別model。

        Raises:
            HTTPException: 対象不在、またはuserから参照されている場合。
        """
        db_obj = self.get_or_404(db, id)
        user_count = db.query(User).filter(User.user_type_id == id).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"この社員種別は{user_count}人のユーザーに割り当てられているため削除できません",
            )

        db.delete(db_obj)
        db.flush()
        return db_obj


user_type = CRUDUserType(UserType)
