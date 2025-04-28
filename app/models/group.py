"""
グループモデル定義
================

ユーザーグループのSQLAlchemyモデル。
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Group(Base):  # type: ignore
    """ユーザーのグループを表すモデル"""

    __tablename__ = "groups"

    group_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    # Userモデルとのリレーションシップ定義 (一対多)
    users = relationship("User", back_populates="group")
    
    def __str__(self) -> str:
        """オブジェクトの文字列表現としてグループ名を返します。"""
        return str(self.name) if self.name is not None else "" 