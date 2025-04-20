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
    color_code = Column(String, nullable=True)  # UIのためのオプションの色コード
