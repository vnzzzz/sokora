"""
カスタム祝日モデル定義
====================

ユーザーが画面から追加する祝日を保持するモデル。
"""

import datetime

from sqlalchemy import Column, Date, Integer, String, UniqueConstraint, DateTime

from app.db.session import Base


class CustomHoliday(Base):  # type: ignore
    """ユーザー追加の祝日を表すモデル"""

    __tablename__ = "custom_holidays"
    __table_args__ = (UniqueConstraint("date", name="uq_custom_holidays_date"),)

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    def __str__(self) -> str:
        """祝日名を返す"""
        return str(self.name) if self.name is not None else ""
