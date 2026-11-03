"""名前付きmaster entityに共通するvalidationとtransaction orchestration。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db.session import Base
from app.services.transaction import transaction

ModelT = TypeVar("ModelT", bound="Base")  # type: ignore
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)


@dataclass(frozen=True)
class NamedMasterMessages:
    """entity固有のpublic error detail。"""

    required_name: str
    duplicate_create: str
    duplicate_update: str
    delete_integrity: str


class NamedMasterService(Generic[ModelT, CreateT, UpdateT]):
    """名前付きmasterの共通service behaviorを提供する小さなabstraction。

    CRUDは従来どおりflush-onlyで、commit/rollbackはこのservice layerが所有する。
    entity固有のlookupとID解釈はcallableとして明示注入し、runtime reflectionには依存しない。

    Args:
        crud: 対象entityのCRUD adapter。
        get_by_name: 名前でentityを取得するlookup callable。
        get_id: entityからinteger IDを取得するcallable。
        messages: validation/integrity failureへ使うpublic error detail。
    """

    def __init__(
        self,
        *,
        crud: CRUDBase[ModelT, CreateT, UpdateT],
        get_by_name: Callable[[Session, str], ModelT | None],
        get_id: Callable[[ModelT], int],
        messages: NamedMasterMessages,
    ) -> None:
        self._crud = crud
        self._get_by_name = get_by_name
        self._get_id = get_id
        self._messages = messages

    def validate_creation(self, db: Session, *, name: str | None) -> None:
        """必須名とcreate時の重複を検証する。

        Args:
            db: DB session。
            name: 作成予定の名称。

        Raises:
            HTTPException: 名称が空、または既存entityと重複する場合。
        """
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self._messages.required_name,
            )
        if self._get_by_name(db, name) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self._messages.duplicate_create,
            )

    def validate_update(
        self,
        db: Session,
        *,
        object_id: int,
        name: str | None,
    ) -> None:
        """必須名と、自身を除外したupdate時の重複を検証する。

        Args:
            db: DB session。
            object_id: 更新対象entity ID。
            name: 更新後の名称。

        Raises:
            HTTPException: 名称が空、または別entityと重複する場合。
        """
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self._messages.required_name,
            )
        existing = self._get_by_name(db, name)
        if existing is not None and self._get_id(existing) != object_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self._messages.duplicate_update,
            )

    def create(
        self,
        db: Session,
        *,
        obj_in: CreateT,
        name: str | None,
    ) -> ModelT:
        """validationからcreateまでを1 transactionで実行する。

        Args:
            db: DB session。
            obj_in: create schema。
            name: validation対象の名称。

        Returns:
            作成後のentity。

        Raises:
            HTTPException: 名称validationに失敗した場合。
            ApplicationError: DB一意制約等のintegrity conflictが発生した場合。
        """
        with transaction(db, integrity_detail=self._messages.duplicate_create):
            self.validate_creation(db, name=name)
            created = self._crud.create(db, obj_in=obj_in)
        return created

    def update(
        self,
        db: Session,
        *,
        object_id: int,
        obj_in: UpdateT,
        name: str | None,
    ) -> ModelT:
        """対象取得・validation・updateを1 transactionで実行する。

        Args:
            db: DB session。
            object_id: 更新対象entity ID。
            obj_in: update schema。
            name: validation対象の名称。

        Returns:
            更新後のentity。

        Raises:
            HTTPException: 対象不在または名称validationに失敗した場合。
            ApplicationError: DB integrity conflictが発生した場合。
        """
        with transaction(db, integrity_detail=self._messages.duplicate_update):
            db_obj = self._crud.get_or_404(db, id=object_id)
            self.validate_update(db, object_id=object_id, name=name)
            updated = self._crud.update(db, db_obj=db_obj, obj_in=obj_in)
        return updated

    def delete(self, db: Session, *, object_id: int) -> ModelT:
        """deleteを1 transactionで実行し、DB参照競合をentity固有detailへ正規化する。

        Args:
            db: DB session。
            object_id: 削除対象entity ID。

        Returns:
            削除したentity。

        Raises:
            HTTPException: 対象entityが存在しない場合。
            ApplicationError: DB参照制約等により削除できない場合。
        """
        with transaction(db, integrity_detail=self._messages.delete_integrity):
            deleted = self._crud.remove(db, id=object_id)
        return deleted
