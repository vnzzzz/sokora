"""
CRUDベースクラス
==============

どのモデルでも使用できる汎用CRUD操作を提供します。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import typing

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

from ..db.session import Base

# ここでの型バインドは文字列として指定
ModelType = TypeVar("ModelType", bound="Base")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基本的なCRUD操作のための汎用クラス
    """

    def __init__(self, model: Type[ModelType]):
        """
        CRUDクラスを初期化する

        Args:
            model: SQLAlchemyモデルクラス
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        IDによるオブジェクト取得

        Args:
            db: データベースセッション
            id: オブジェクトのID

        Returns:
            Optional[ModelType]: 見つかったオブジェクト、またはNone
        """
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        複数オブジェクトの取得

        Args:
            db: データベースセッション
            skip: スキップする件数
            limit: 取得する最大件数

        Returns:
            List[ModelType]: オブジェクトのリスト
        """
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        新しいオブジェクトを作成

        Args:
            db: データベースセッション
            obj_in: 作成するオブジェクトのデータ

        Returns:
            ModelType: 作成されたオブジェクト
        """
        # jsonable_encoderを使用せず、直接dictに変換
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """
        オブジェクトを更新

        Args:
            db: データベースセッション
            db_obj: 更新するデータベースオブジェクト
            obj_in: 更新データ（スキーマまたは辞書）

        Returns:
            ModelType: 更新されたオブジェクト
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """
        オブジェクトを削除

        Args:
            db: データベースセッション
            id: 削除するオブジェクトのID

        Returns:
            ModelType: 削除されたオブジェクト
        """
        obj = db.query(self.model).get(id)
        if obj is None:
            raise ValueError(f"Object with id {id} not found")
        db.delete(obj)
        db.commit()
        return obj
