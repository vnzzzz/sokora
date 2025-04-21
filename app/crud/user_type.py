"""
社員種別CRUD操作
==============

社員種別モデルに対するCRUD操作を提供します。
"""

from typing import Any, Dict, Optional, Union, List

from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.user_type import UserType
from ..schemas.user_type import UserTypeCreate, UserTypeUpdate


class CRUDUserType(CRUDBase[UserType, UserTypeCreate, UserTypeUpdate]):
    """社員種別に対するCRUD操作クラス"""

    def get_by_id(self, db: Session, user_type_id: int) -> Optional[UserType]:
        """IDによる社員種別取得

        Args:
            db: データベースセッション
            user_type_id: 社員種別ID

        Returns:
            Optional[UserType]: 見つかった社員種別またはNone
        """
        return db.query(UserType).filter(UserType.user_type_id == user_type_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[UserType]:
        """名前による社員種別取得

        Args:
            db: データベースセッション
            name: 社員種別名

        Returns:
            Optional[UserType]: 見つかった社員種別またはNone
        """
        return db.query(UserType).filter(UserType.name == name).first()

    def create(self, db: Session, *, obj_in: UserTypeCreate) -> UserType:
        """新しい社員種別を作成

        Args:
            db: データベースセッション
            obj_in: 作成する社員種別のデータ

        Returns:
            UserType: 作成された社員種別
        """
        db_obj = UserType(
            name=obj_in.name,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: UserType,
        obj_in: Union[UserTypeUpdate, Dict[str, Any]],
    ) -> UserType:
        """社員種別を更新

        Args:
            db: データベースセッション
            db_obj: 更新する社員種別
            obj_in: 更新データ

        Returns:
            UserType: 更新された社員種別
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def remove(self, db: Session, *, id: Any) -> UserType:
        """社員種別を削除

        Args:
            db: データベースセッション
            id: 削除する社員種別のID

        Returns:
            UserType: 削除された社員種別
        """
        obj = db.query(UserType).filter(UserType.user_type_id == id).first()
        if obj is None:
            raise ValueError(f"UserType with id {id} not found")
        db.delete(obj)
        db.commit()
        return obj

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserType]:
        """複数社員種別の取得

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            List[UserType]: 社員種別のリスト
        """
        return db.query(UserType).order_by(UserType.name).offset(skip).limit(limit).all()


user_type = CRUDUserType(UserType) 