"""
ユーザーCRUD操作
==================

ユーザーモデルの作成、読取、更新、削除操作を提供します。
"""

from typing import List, Tuple

from sqlalchemy.orm import Session

from .base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """ユーザーモデルのCRUD操作クラス"""

    def get_username_by_id(self, db: Session, *, id: str) -> str:
        """
        ユーザーIDからユーザー名を取得

        Args:
            db: データベースセッション
            id: ユーザーID文字列

        Returns:
            str: ユーザー名（見つからない場合は空文字）
        """
        user = self.get(db, id=id)
        if user:
            return str(user.username)
        return ""

    def get_all_users(self, db: Session) -> List[Tuple[str, str, int]]:
        """
        すべてのユーザーを取得

        Args:
            db: データベースセッション

        Returns:
            List[Tuple[str, str, int]]: (username, id, user_type_id) のタプルリスト
        """
        users = db.query(User).all()
        return [(str(user.username), str(user.id), int(user.user_type_id)) for user in users]


user = CRUDUser(User)
