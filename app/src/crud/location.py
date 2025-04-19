"""
Location CRUD operations
=====================

Create, Read, Update, Delete operations for Location model.
"""

from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.location import Location
from ..schemas.location import LocationCreate, LocationUpdate


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

    def create_with_name(
        self, db: Session, *, name: str, color_code: Optional[str] = None
    ) -> Location:
        """
        名前を指定して新しい勤務場所を作成

        Args:
            db: データベースセッション
            name: 勤務場所名
            color_code: 色コード（オプション）

        Returns:
            Location: 作成された勤務場所
        """
        # 既存の勤務場所を確認
        existing = self.get_by_name(db, name=name)
        if existing:
            return existing

        # 新しい勤務場所を作成
        location_in = LocationCreate(name=name, color_code=color_code)
        return self.create(db, obj_in=location_in)

    def get_all_locations(self, db: Session) -> List[str]:
        """
        すべての勤務場所名を取得

        Args:
            db: データベースセッション

        Returns:
            List[str]: 勤務場所名のリスト
        """
        locations = db.query(Location).all()
        return [loc.name for loc in locations]

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


location = CRUDLocation(Location)
