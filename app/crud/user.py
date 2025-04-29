"""
ユーザーCRUD操作
==================

ユーザーモデルの作成、読取、更新、削除操作を提供します。
"""

from typing import List, Tuple, Optional

from sqlalchemy.orm import Session, joinedload

from .base import CRUDBase
from app.models.user import User
from app.models.group import Group
from app.models.user_type import UserType
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

    def get_all_users_with_details(
        self, db: Session
    ) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
        """
        全てのユーザー情報を関連情報（グループ名、ユーザータイプ名）と共に取得します。
        
        Returns:
            List[Tuple[str, str, Optional[str], Optional[str]]]: 
                (username, user_id, group_name, user_type_name) のリスト
        """
        results = (
            db.query(
                User.username,
                User.id,
                Group.name.label("group_name"),
                UserType.name.label("user_type_name"),
            )
            .outerjoin(Group, User.group_id == Group.id)
            .outerjoin(UserType, User.user_type_id == UserType.id)
            .order_by(User.username)
            .all()
        )
        # 結果をタプルのリストとして返す
        return [
            (
                res.username, 
                res.id, 
                res.group_name, 
                res.user_type_name
            ) 
            for res in results
        ]


user = CRUDUser(User)
