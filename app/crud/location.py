"""
勤怠種別CRUD操作
=====================

勤怠種別モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import asc, func, nullslast
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate

from .base import CRUDBase


def _display_category_sort_key(category: Any) -> Any:
    """画面上の未分類値を同一categoryとしてNULL lastにするsort expressionを返す。

    Args:
        category: SQLAlchemyのcategory column/expression。

    Returns:
        空文字・`未分類`・NULLを未分類として扱うORDER BY expression。
    """
    normalized = func.nullif(func.nullif(category, ""), "未分類")
    return nullslast(asc(normalized))


class CRUDLocation(CRUDBase[Location, LocationCreate, LocationUpdate]):
    """勤怠種別固有の検索・並び順・参照チェックを追加したCRUD操作。"""

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Location]:
        """表示上のcategory、order、ID順で勤怠種別を取得する。

        Args:
            db: DB session。
            skip: 先頭からskipする件数。
            limit: 最大取得件数。

        Returns:
            pagination適用済みの勤怠種別list。
        """
        return (
            db.query(self.model)
            .order_by(
                _display_category_sort_key(self.model.category),
                nullslast(asc(self.model.order)),
                asc(self.model.id),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session) -> List[Location]:
        """全勤怠種別を表示上のcategory、order、ID順で取得する。

        空文字category、NULL、literal「未分類」は画面上同じgroupなので同一sort keyとして扱う。
        paginationを持たないmaster/read pathで完全な勤怠種別集合を扱うための共通read。

        Args:
            db: DB session。

        Returns:
            全勤怠種別のlist。
        """
        return (
            db.query(self.model)
            .order_by(
                _display_category_sort_key(self.model.category),
                nullslast(asc(self.model.order)),
                asc(self.model.id),
            )
            .all()
        )

    def get_by_name(self, db: Session, *, name: str) -> Optional[Location]:
        """勤怠種別名で1件取得する。

        Args:
            db: DB session。
            name: 検索する勤怠種別名。

        Returns:
            一致する勤怠種別。存在しない場合は`None`。
        """
        return db.query(Location).filter(Location.name == name).first()

    def create_with_name(self, db: Session, *, name: str) -> Location:
        """同名entityを再利用し、無い場合だけ新規行をflushする。

        Args:
            db: DB session。
            name: 取得または作成する勤怠種別名。

        Returns:
            既存または新規flush済みの勤怠種別model。
        """
        existing = self.get_by_name(db, name=name)
        if existing:
            return existing
        return self.create(db, obj_in=LocationCreate(name=name))

    def get_or_create_multiple(
        self, db: Session, *, location_names: List[str]
    ) -> Dict[str, Location]:
        """複数名称について既存または新規flush済みentityを返す。

        Args:
            db: DB session。
            location_names: 取得/作成対象の名称list。空文字は無視する。

        Returns:
            入力名称をkey、対応する勤怠種別modelをvalueとするmapping。
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
        """未使用の勤怠種別を削除対象としてflushする。

        勤怠から参照されている場合は利用者向け400を返すため事前チェックする。並行writeとの
        競合時はDB FK制約が最終的な参照整合性を保証する。commit/rollbackはserviceが所有する。

        Args:
            db: DB session。
            id: 削除対象の勤怠種別ID。

        Returns:
            削除stage済みの勤怠種別model。

        Raises:
            HTTPException: 対象不在、または勤怠から参照されている場合。
        """
        db_obj = self.get_or_404(db, id)
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
