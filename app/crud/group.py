"""
グループCRUD操作
==============

グループモデルに対するCRUD操作を提供します。
"""

from typing import Any, Dict, Optional, Union, List

from sqlalchemy.orm import Session

from .base import CRUDBase
from app.models.group import Group
from app.schemas.group import GroupCreate, GroupUpdate


class CRUDGroup(CRUDBase[Group, GroupCreate, GroupUpdate]):
    """グループに対するCRUD操作クラス"""

    def get_by_id(self, db: Session, group_id: int) -> Optional[Group]:
        """IDによるグループ取得

        Args:
            db: データベースセッション
            group_id: グループID

        Returns:
            Optional[Group]: 見つかったグループまたはNone
        """
        return db.query(Group).filter(Group.group_id == group_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Group]:
        """名前によるグループ取得

        Args:
            db: データベースセッション
            name: グループ名

        Returns:
            Optional[Group]: 見つかったグループまたはNone
        """
        return db.query(Group).filter(Group.name == name).first()

    def create(self, db: Session, *, obj_in: GroupCreate) -> Group:
        """新しいグループを作成

        Args:
            db: データベースセッション
            obj_in: 作成するグループのデータ

        Returns:
            Group: 作成されたグループ
        """
        db_obj = Group(
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
        db_obj: Group,
        obj_in: Union[GroupUpdate, Dict[str, Any]],
    ) -> Group:
        """グループを更新

        Args:
            db: データベースセッション
            db_obj: 更新するグループ
            obj_in: 更新データ

        Returns:
            Group: 更新されたグループ
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def remove(self, db: Session, *, id: Any) -> Group:
        """グループを削除

        Args:
            db: データベースセッション
            id: 削除するグループのID

        Returns:
            Group: 削除されたグループ
        """
        obj = db.query(Group).filter(Group.group_id == id).first()
        if obj is None:
            raise ValueError(f"Group with id {id} not found")
        db.delete(obj)
        db.commit()
        return obj

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Group]:
        """複数グループの取得

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            List[Group]: グループのリスト
        """
        return db.query(Group).offset(skip).limit(limit).all()


group = CRUDGroup(Group) 