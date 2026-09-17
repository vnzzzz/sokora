"""
CRUDベースクラス
==============

どのモデルでも使用できる汎用CRUD操作を提供します。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import Base

ModelType = TypeVar("ModelType", bound="Base")  # type: ignore
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """SQLAlchemyモデル向けの共通CRUD操作。

    write操作は ``flush()`` までを担当し、``commit()`` / ``rollback()`` は
    呼び出し側のserviceがuse case単位で所有します。

    Args:
        model: CRUD対象のSQLAlchemy model class。
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """主キーで1件取得する。

        Args:
            db: DB session。
            id: 取得対象のprimary key。

        Returns:
            一致するmodel。存在しない場合は`None`。
        """
        return db.query(self.model).filter(self.model.id == id).first()

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """主キーで1件取得し、不在時は404を送出する。

        Args:
            db: DB session。
            id: 取得対象のprimary key。

        Returns:
            一致するmodel。

        Raises:
            HTTPException: 対象modelが存在しない場合。
        """
        db_obj = self.get(db, id)
        if db_obj is None:
            model_name = self.model.__name__
            raise HTTPException(
                status_code=404, detail=f"{model_name} with id {id} not found"
            )
        return db_obj

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """offset/limit付きでmodel一覧を取得する。

        Args:
            db: DB session。
            skip: 先頭からskipする件数。
            limit: 最大取得件数。

        Returns:
            対象modelのlist。
        """
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """新規行を追加してflushする。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackする。

        Args:
            db: DB session。
            obj_in: create schema。

        Returns:
            DB生成値をrefresh済みのmodel。
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """指定modelへ更新値を適用してflushする。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackする。

        Args:
            db: DB session。
            db_obj: 更新対象model。
            obj_in: update schemaまたはfield/value mapping。

        Returns:
            refresh済みの更新後model。
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """主キーで対象を削除してflushする。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackする。

        Args:
            db: DB session。
            id: 削除対象のprimary key。

        Returns:
            削除stage済みのmodel。

        Raises:
            ValueError: 対象modelが存在しない場合。
        """
        obj = db.get(self.model, id)
        if obj is None:
            raise ValueError(f"ID {id} のオブジェクトが見つかりません")
        db.delete(obj)
        db.flush()
        return obj
