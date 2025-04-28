"""
ユーザーモデル定義
================

ユーザーのSQLAlchemyモデル。
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):  # type: ignore
    """システム内の社員を表すユーザーモデル"""

    __tablename__ = "users"

    user_id = Column(String, primary_key=True, nullable=False, index=True)
    username = Column(String, nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    user_type_id = Column(Integer, ForeignKey("user_types.user_type_id"), nullable=False)

    # Groupモデルとのリレーションシップ定義 (多対一)
    group = relationship("Group", back_populates="users")
    # UserTypeモデルとのリレーションシップ定義 (多対一)
    user_type = relationship("UserType", back_populates="users")
    # Attendanceモデルとのリレーションシップ定義 (一対多)
    attendance_records = relationship("Attendance", back_populates="user")
