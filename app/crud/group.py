"""
グループCRUD操作
==============

グループモデルに対するCRUD操作を提供します。
"""

from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .base import CRUDBase
from app.models.group import Group
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate


class CRUDGroup(CRUDBase[Group, GroupCreate, GroupUpdate]):
    """グループに対するCRUD操作クラス"""

    def get_by_name(self, db: Session, name: str) -> Optional[Group]:
        """名前によるグループ取得

        Args:
            db: データベースセッション
            name: グループ名

        Returns:
            Optional[Group]: 見つかったグループまたはNone
        """
        return db.query(Group).filter(Group.name == name).first()

    def remove(self, db: Session, *, id: int) -> Group:
        """グループを削除 (関連ユーザーがいない場合のみ)

        Args:
            db: データベースセッション
            id: 削除するグループのID

        Returns:
            Group: 削除されたグループ

        Raises:
            HTTPException: グループが見つからない場合 (404)
            HTTPException: グループに関連ユーザーが存在する場合 (400)
        """
        # まずオブジェクトが存在するか確認 (なければ404)
        db_obj = self.get_or_404(db, id)
        
        # 関連するユーザーがいないかチェック
        user_count = db.query(User).filter(User.group_id == id).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"このグループは{user_count}人のユーザーに割り当てられているため削除できません"
            )
        
        # 依存関係がなければ削除を実行
        db.delete(db_obj)
        db.commit()
        return db_obj

group = CRUDGroup(Group) 