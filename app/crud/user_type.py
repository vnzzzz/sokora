"""
社員種別CRUD操作
==============

社員種別モデルに対するCRUD操作を提供します。
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from .base import CRUDBase
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate, UserTypeUpdate
from fastapi import HTTPException, status


class CRUDUserType(CRUDBase[UserType, UserTypeCreate, UserTypeUpdate]):
    """社員種別に対するCRUD操作クラス"""

    def get_by_name(self, db: Session, name: str) -> Optional[UserType]:
        """名前による社員種別取得

        Args:
            db: データベースセッション
            name: 社員種別名

        Returns:
            Optional[UserType]: 見つかった社員種別またはNone
        """
        return db.query(UserType).filter(UserType.name == name).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserType]:
        """複数社員種別の取得 (order順、次にname順でソート)

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            List[UserType]: 社員種別のリスト
        """
        return db.query(UserType)\
            .order_by(UserType.order.nullslast(), UserType.name)\
            .offset(skip).limit(limit).all()

    def remove(self, db: Session, *, id: int) -> UserType:
        """社員種別を削除 (関連ユーザーがいない場合のみ)

        Args:
            db: データベースセッション
            id: 削除する社員種別のID

        Returns:
            UserType: 削除された社員種別

        Raises:
            HTTPException: 社員種別が見つからない場合 (404)
            HTTPException: 社員種別に関連ユーザーが存在する場合 (400)
        """
        db_obj = self.get_or_404(db, id)
        
        user_count = db.query(User).filter(User.user_type_id == id).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"この社員種別は{user_count}人のユーザーに割り当てられているため削除できません"
            )
            
        db.delete(db_obj)
        db.commit()
        return db_obj


user_type = CRUDUserType(UserType) 