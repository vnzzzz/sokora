"""
勤怠記録モデル定義
===============

ユーザーの勤怠記録を管理するSQLAlchemyモデル。
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Attendance(Base):  # type: ignore
    """ユーザーの日々の勤務場所を表す勤怠モデル"""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)

    # Userモデルとのリレーションシップ定義 (多対一)
    user = relationship("User", back_populates="attendance_records")
    # Locationモデルとのリレーションシップ定義 (多対一)
    location_info = relationship("Location", back_populates="attendances")

    # SQLAlchemyのUniqueConstraintを使って複合ユニーク制約を定義
    # (ユーザーIDと日付の組み合わせが一意であることを保証)
    # from sqlalchemy import UniqueConstraint
    # __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)
    # ConfigクラスはPydanticで使用されるもので、SQLAlchemyモデルでは通常 __table_args__ を使用します。
    # ただし、既存の動作を維持するため、ここではコメントアウトのままにします。
    # class Config:
    #     unique_together = ("user_id", "date")
