"""
勤務場所CRUD操作
=====================

勤務場所モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.location import Location
from ..schemas.location import LocationCreate, LocationUpdate
from ..core.config import logger


class CRUDLocation(CRUDBase[Location, LocationCreate, LocationUpdate]):
    """勤務場所モデルのCRUD操作クラス"""

    def get_by_name(self, db: Session, *, name: str) -> Optional[Location]:
        """
        名前で勤務場所を取得

        Args:
            db: データベースセッション
            name: 勤務場所名

        Returns:
            Optional[Location]: 見つかった勤務場所、またはNone
        """
        return db.query(Location).filter(Location.name == name).first()

    def get_by_id(self, db: Session, *, location_id: int) -> Optional[Location]:
        """
        IDで勤務場所を取得

        Args:
            db: データベースセッション
            location_id: 勤務場所ID

        Returns:
            Optional[Location]: 見つかった勤務場所、またはNone
        """
        return db.query(Location).filter(Location.location_id == location_id).first()

    def create_with_name(
        self, db: Session, *, name: str
    ) -> Location:
        """
        名前を指定して新しい勤務場所を作成

        Args:
            db: データベースセッション
            name: 勤務場所名

        Returns:
            Location: 作成された勤務場所
        """
        # 既存の勤務場所を確認
        existing = self.get_by_name(db, name=name)
        if existing:
            return existing

        # 新しい勤務場所を作成
        location_in = LocationCreate(name=name)
        return self.create(db, obj_in=location_in)

    def get_all_locations(self, db: Session) -> List[str]:
        """
        すべての勤務場所名を取得

        Args:
            db: データベースセッション

        Returns:
            List[str]: 勤務場所名のリスト
        """
        try:
            locations = db.query(Location).all()
            return [str(loc.name) for loc in locations]
        except Exception as e:
            logger.error(f"Error getting location types: {str(e)}")
            return []

    def get_location_dict(self, db: Session) -> Dict[int, str]:
        """
        すべての勤務場所をID:名前の辞書として取得

        Args:
            db: データベースセッション

        Returns:
            Dict[int, str]: location_idをキー、名前を値とする辞書
        """
        try:
            locations = db.query(Location).all()
            return {int(loc.location_id): str(loc.name) for loc in locations}
        except Exception as e:
            logger.error(f"Error getting location dict: {str(e)}")
            return {}

    def get_or_create_multiple(
        self, db: Session, *, location_names: List[str]
    ) -> Dict[str, Location]:
        """
        複数の勤務場所を取得または作成

        Args:
            db: データベースセッション
            location_names: 勤務場所名のリスト

        Returns:
            Dict[str, Location]: 勤務場所名をキーとする勤務場所オブジェクトの辞書
        """
        result = {}
        for name in location_names:
            if not name.strip():
                continue
            location = self.get_by_name(db, name=name)
            if not location:
                location = self.create_with_name(db, name=name)
            result[name] = location
        return result

    def remove(self, db: Session, *, id: int) -> Location:
        """
        勤務場所を削除する

        Args:
            db: データベースセッション
            id: 勤務場所ID

        Returns:
            Location: 削除された勤務場所
        """
        location = self.get_by_id(db, location_id=id)
        if location is None:
            raise ValueError(f"勤務場所ID {id} が見つかりません")
        db.delete(location)
        db.commit()
        return location


location = CRUDLocation(Location)
