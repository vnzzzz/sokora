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
        """社員種別名で1件取得し、存在しない場合は ``None`` を返します。"""
        return db.query(UserType).filter(UserType.name == name).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserType]:
        """``order``、次に名前の順で社員種別一覧を取得します。"""
        return (
            db.query(UserType)
            .order_by(UserType.order.nullslast(), UserType.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def remove(self, db: Session, *, id: int) -> UserType:
        """未使用の社員種別を削除対象としてflushし、削除対象を返します。

        ユーザーから参照されている場合はHTTP 400を送出します。commit/rollbackは
        呼び出し側serviceが所有します。
        """
        db_obj = self.get_or_404(db, id)

        # この事前チェックは利用者向けエラーのために行う。
        # 並行writeとの競合時はDBのFK制約が最終的な参照整合性を保証する。
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
