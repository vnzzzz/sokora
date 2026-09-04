"""
勤怠種別CRUD操作
=====================

勤怠種別モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import asc, nullslast
from sqlalchemy.orm import Session

from app.core.config import logger
from app.models.attendance import Attendance
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate

from .base import CRUDBase


class CRUDLocation(CRUDBase[Location, LocationCreate, LocationUpdate]):
    """勤怠種別固有の検索・並び順・参照チェックを追加したCRUD操作。"""

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Location]:
        """category、order、IDの順で勤怠種別一覧を取得します。"""
        return (
            db.query(self.model)
            .order_by(
                nullslast(asc(self.model.category)),
                nullslast(asc(self.model.order)),
                asc(self.model.id),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session) -> List[Location]:
        """paginationせず、全勤怠種別をcategory、order、ID順で取得する。

        analysis等、完全なmaster集合をprojection boundaryとして利用するread向け。
        page/API paginationを意図するcallerは :meth:`get_multi` を利用する。
        """
        return (
            db.query(self.model)
            .order_by(
                nullslast(asc(self.model.category)),
                nullslast(asc(self.model.order)),
                asc(self.model.id),
            )
            .all()
        )

    def get_by_name(self, db: Session, *, name: str) -> Optional[Location]:
        """勤怠種別名で1件取得し、存在しない場合は ``None`` を返します。"""
        return db.query(Location).filter(Location.name == name).first()

    def create_with_name(self, db: Session, *, name: str) -> Location:
        """同名の勤怠種別を再利用し、無い場合だけ新規行をflushします。"""
        existing = self.get_by_name(db, name=name)
        if existing:
            return existing
        return self.create(db, obj_in=LocationCreate(name=name))

    def get_all_locations(self, db: Session) -> List[str]:
        """表示順に並べた勤怠種別名だけを返します。取得失敗時は空listです。"""
        try:
            locations = (
                db.query(Location)
                .order_by(
                    nullslast(asc(Location.category)),
                    nullslast(asc(Location.order)),
                    asc(Location.id),
                )
                .all()
            )
            return [str(loc.name) for loc in locations]
        except Exception as e:
            logger.error(f"Error getting location types: {str(e)}")
            return []

    def get_location_dict(self, db: Session) -> Dict[int, str]:
        """勤怠種別を ``{id: name}`` 形式で返します。取得失敗時は空dictです。"""
        try:
            locations = (
                db.query(Location)
                .order_by(
                    nullslast(asc(Location.category)),
                    nullslast(asc(Location.order)),
                    asc(Location.id),
                )
                .all()
            )
            return {int(loc.id): str(loc.name) for loc in locations}
        except Exception as e:
            logger.error(f"Error getting location dict: {str(e)}")
            return {}

    def get_or_create_multiple(
        self, db: Session, *, location_names: List[str]
    ) -> Dict[str, Location]:
        """空文字を除外し、各名前の既存行または新規flush済み行を返します。"""
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
        """未使用の勤怠種別を削除対象としてflushし、削除対象を返します。

        勤怠から参照されている場合はHTTP 400を送出します。commit/rollbackは
        呼び出し側serviceが所有します。
        """
        db_obj = self.get_or_404(db, id)

        # この事前チェックは利用者向けエラーのために行う。
        # 並行writeとの競合時はDBのFK制約が最終的な参照整合性を保証する。
        attendance_count = (
            db.query(Attendance).filter(Attendance.location_id == id).count()
        )
        if attendance_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"この勤怠種別は{attendance_count}件の勤怠データで使用されているため削除できません",
            )

        db.delete(db_obj)
        db.flush()
        return db_obj


location = CRUDLocation(Location)
