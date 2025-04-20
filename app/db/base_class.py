"""
SQLAlchemy base class
=====================

Base class for SQLAlchemy ORM models.
"""

from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """Base class for all SQLAlchemy models"""

    id: Any
    __name__: str

    # Generate tablename automatically based on class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
