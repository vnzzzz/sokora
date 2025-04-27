"""
勤務場所モデル定義
================

勤務場所タイプのSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class Location(Base):  # type: ignore
    """勤務場所タイプを表すモデル"""

    __tablename__ = "locations"

    location_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    # 関連する勤怠記録
    attendances = relationship("Attendance", back_populates="location_info")
    
    def __str__(self) -> str:
        """オブジェクトの文字列表現として勤務場所名を返します。"""
        return str(self.name) if self.name is not None else ""
