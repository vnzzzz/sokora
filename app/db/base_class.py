"""
SQLAlchemyベースクラス
=====================

SQLAlchemyのORMモデル用の基底クラスを定義します。
すべてのデータモデルはこのクラスを継承して作成されます。
"""

from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """SQLAlchemyの全モデルの基底クラス

    共通の属性とふるまいを提供し、モデル定義を簡略化します。
    """

    id: Any
    __name__: str

    # クラス名からテーブル名を自動生成するメソッド
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
