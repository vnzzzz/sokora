"""
勤務場所CRUD操作
=====================

勤務場所モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .base import CRUDBase
from app.models.attendance import Attendance
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate
from app.core.config import logger


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
            return {int(loc.id): str(loc.name) for loc in locations}
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
        """勤務場所を削除 (関連勤怠記録がない場合のみ)

        Args:
            db: データベースセッション
            id: 削除する勤務場所のID

        Returns:
            Location: 削除された勤務場所

        Raises:
            HTTPException: 勤務場所が見つからない場合 (404)
            HTTPException: 勤務場所に関連勤怠記録が存在する場合 (400)
        """
        db_obj = self.get_or_404(db, id)
        
        attendance_count = db.query(Attendance).filter(Attendance.location_id == id).count()
        if attendance_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"この勤務場所は{attendance_count}件の勤怠データで使用されているため削除できません"
            )
        
        db.delete(db_obj)
        db.commit()
        return db_obj


location = CRUDLocation(Location)
