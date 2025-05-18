"""
勤怠種別モデル定義
================

勤怠種別タイプのSQLAlchemyモデル。
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Location(Base):  # type: ignore
    """勤怠種別タイプを表すモデル"""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=True, index=True)
    order = Column(Integer, nullable=True)
    
    # 関連する勤怠記録
    attendances = relationship("Attendance", back_populates="location_info")
    
    def __str__(self) -> str:
        """オブジェクトの文字列表現として勤怠種別名を返します。"""
        return str(self.name) if self.name is not None else ""
