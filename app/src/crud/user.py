"""
User CRUD operations
==================

Create, Read, Update, Delete operations for User model.
"""

from typing import Any, Dict, Optional, Union, List, Tuple

from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.user import User
from ..models.attendance import Attendance
from ..schemas.user import UserCreate, UserUpdate
from ..core.config import logger


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """ユーザーモデルのCRUD操作クラス"""

    def get_by_user_id(self, db: Session, *, user_id: str) -> Optional[User]:
        """
        user_idフィールドでユーザーを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列

        Returns:
            Optional[User]: 見つかったユーザー、またはNone
        """
        return db.query(User).filter(User.user_id == user_id).first()

    def get_user_name_by_id(self, db: Session, *, user_id: str) -> str:
        """
        ユーザーIDからユーザー名を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列

        Returns:
            str: ユーザー名（見つからない場合は空文字）
        """
        user = self.get_by_user_id(db, user_id=user_id)
        return user.username if user else ""

    def create_with_id(
        self, db: Session, *, obj_in: Union[UserCreate, Dict[str, Any]]
    ) -> User:
        """
        ユーザーIDを指定して新しいユーザーを作成

        Args:
            db: データベースセッション
            obj_in: 作成するユーザーのデータ

        Returns:
            User: 作成されたユーザー
        """
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.dict()

        db_obj = User(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_user(self, db: Session, *, username: str, user_id: str) -> bool:
        """
        新しいユーザーを作成（簡易インターフェース）

        Args:
            db: データベースセッション
            username: ユーザー名
            user_id: ユーザーID

        Returns:
            bool: 成功したかどうか
        """
        try:
            # 既存ユーザーをチェック
            existing_user = self.get_by_user_id(db, user_id=user_id)
            if existing_user:
                return False

            # 新しいユーザーを作成
            user_in = UserCreate(username=username, user_id=user_id)
            self.create(db, obj_in=user_in)
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding user: {str(e)}")
            return False

    def delete_user(self, db: Session, *, user_id: str) -> bool:
        """
        ユーザーを削除

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            bool: 成功したかどうか
        """
        try:
            user = self.get_by_user_id(db, user_id=user_id)
            if not user:
                return False

            # 関連する出席レコードも削除
            db.query(Attendance).filter(Attendance.user_id == user.id).delete()

            # ユーザーを削除
            db.delete(user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def get_all_users(self, db: Session) -> List[Tuple[str, str]]:
        """
        すべてのユーザーを取得

        Args:
            db: データベースセッション

        Returns:
            List[Tuple[str, str]]: (username, user_id) のタプルリスト
        """
        users = db.query(User).all()
        return [(user.username, user.user_id) for user in users]


user = CRUDUser(User)
