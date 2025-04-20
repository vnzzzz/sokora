"""
グループモデル定義
================

ユーザーグループのSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from ..db.session import Base


class Group(Base):  # type: ignore
    """ユーザーのグループを表すモデル"""

    __tablename__ = "groups"

    group_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    # ユーザーとの関連付け
    users = relationship("User", back_populates="group")
    
    def __str__(self) -> str:
        """文字列表現としてname属性を返します"""
        return str(self.name) if self.name is not None else "" 