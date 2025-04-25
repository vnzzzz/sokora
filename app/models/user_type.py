"""
社員種別モデル定義
================

ユーザーの社員種別のSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserType(Base):  # type: ignore
    """ユーザーの社員種別を表すモデル"""

    __tablename__ = "user_types"

    user_type_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    # ユーザーとの関連付け
    users = relationship("User", back_populates="user_type")
    
    def __str__(self) -> str:
        """文字列表現としてname属性を返します"""
        return str(self.name) if self.name is not None else "" 