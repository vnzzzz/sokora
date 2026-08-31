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
    """

    def __init__(self, model: Type[ModelType]):
        """操作対象のSQLAlchemyモデルを指定してCRUDを初期化します。"""
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """主キーで1件取得し、存在しない場合は ``None`` を返します。"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """主キーで1件取得し、存在しない場合はHTTP 404を送出します。"""
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
        """``skip`` と ``limit`` を指定してモデル一覧を取得します。"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """新規行を追加してflushし、生成値を反映したモデルを返します。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackしてください。
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
        """指定モデルへ更新値を適用してflushし、更新後モデルを返します。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackしてください。
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
        """主キーで対象を削除してflushし、削除対象モデルを返します。

        transactionは確定しないため、呼び出し側serviceでcommit/rollbackしてください。
        """
        obj = db.get(self.model, id)
        if obj is None:
            raise ValueError(f"ID {id} のオブジェクトが見つかりません")
        db.delete(obj)
        db.flush()
        return obj
