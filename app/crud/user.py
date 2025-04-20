"""
ユーザーCRUD操作
==================

ユーザーモデルの作成、読取、更新、削除操作を提供します。
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
        return str(user.username) if user else ""

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

    def create_user(self, db: Session, *, username: str, user_id: str, group_id: int, is_contractor: bool = False) -> bool:
        """
        新しいユーザーを作成（簡易インターフェース）

        Args:
            db: データベースセッション
            username: ユーザー名
            user_id: ユーザーID
            group_id: グループID
            is_contractor: 派遣社員かどうか

        Returns:
            bool: 成功したかどうか
        """
        try:
            # 既存ユーザーをチェック
            existing_user = self.get_by_user_id(db, user_id=user_id)
            if existing_user:
                return False

            # 新しいユーザーを作成
            user_in = UserCreate(username=username, user_id=user_id, group_id=group_id, is_contractor=is_contractor)
            self.create(db, obj_in=user_in)
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding user: {str(e)}")
            return False

    def update_user(
        self, 
        db: Session, 
        *, 
        user_id: str, 
        username: str, 
        group_id: int,
        is_contractor: Optional[bool] = None
    ) -> bool:
        """
        ユーザー情報を更新

        Args:
            db: データベースセッション
            user_id: 更新するユーザーID
            username: 新しいユーザー名
            group_id: 新しいグループID
            is_contractor: 新しい派遣社員フラグ（省略可）

        Returns:
            bool: 成功したかどうか
        """
        try:
            db_obj = self.get_by_user_id(db, user_id=user_id)
            if not db_obj:
                return False
                
            setattr(db_obj, "username", username)
            setattr(db_obj, "group_id", group_id)
                    
            if is_contractor is not None:
                setattr(db_obj, "is_contractor", is_contractor)
                
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user: {str(e)}")
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

            # 関連する勤怠レコードも削除
            db.query(Attendance).filter(Attendance.user_id == user.user_id).delete()

            # ユーザーを削除
            db.delete(user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def get_all_users(self, db: Session) -> List[Tuple[str, str, bool]]:
        """
        すべてのユーザーを取得

        Args:
            db: データベースセッション

        Returns:
            List[Tuple[str, str, bool]]: (username, user_id, is_contractor) のタプルリスト
        """
        users = db.query(User).all()
        return [(str(user.username), str(user.user_id), bool(user.is_contractor)) for user in users]


user = CRUDUser(User)
