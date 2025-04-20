"""
勤務場所モデル定義
================

勤務場所タイプのSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer

from ..db.session import Base


class Location(Base):  # type: ignore
    """勤務場所タイプを表すモデル"""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    def __str__(self) -> str:
        """文字列表現としてname属性を返します"""
        return str(self.name) if self.name is not None else ""
