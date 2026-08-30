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
from app.core.config import logger

# ここでの型バインドは文字列として指定
ModelType = TypeVar("ModelType", bound="Base") #type: ignore
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

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """
        IDによるオブジェクト取得 (見つからない場合は404エラー)

        Args:
            db: データベースセッション
            id: オブジェクトのID

        Returns:
            ModelType: 見つかったオブジェクト
            
        Raises:
            HTTPException: ステータスコード404で見つからなかった場合
        """
        db_obj = self.get(db, id)
        if db_obj is None:
            # モデル名を取得してエラーメッセージに含める
            model_name = self.model.__name__
            raise HTTPException(
                status_code=404, 
                detail=f"{model_name} with id {id} not found"
            )
        return db_obj

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
        try:
            # Pydantic v2互換: dict()からmodel_dump()に変更
            obj_in_data = obj_in.model_dump()
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"オブジェクト作成エラー: {str(e)}", exc_info=True)
            raise

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
        try:
            # obj_data = jsonable_encoder(db_obj) # 不要
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                # Pydantic v2互換: dict()からmodel_dump()に変更
                update_data = obj_in.model_dump(exclude_unset=True)
            # update_data のキーを直接ループして更新
            for field, value in update_data.items():
                # hasattr で存在確認を追加するとより安全
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"オブジェクト更新エラー: {str(e)}", exc_info=True)
            raise

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """
        オブジェクトを削除

        Args:
            db: データベースセッション
            id: 削除するオブジェクトのID

        Returns:
            ModelType: 削除されたオブジェクト
        """
        try:
            # obj = db.query(self.model).get(id) # SQLAlchemy 2.0 で非推奨
            obj = db.get(self.model, id)
            if obj is None:
                raise ValueError(f"ID {id} のオブジェクトが見つかりません")
            db.delete(obj)
            db.commit()
            return obj
        except Exception as e:
            db.rollback()
            logger.error(f"オブジェクト削除エラー: {str(e)}", exc_info=True)
            raise
