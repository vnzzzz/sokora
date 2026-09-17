"""社員種別関連のvalidationとtransaction境界を提供するservice。"""

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.named_master_service import NamedMasterMessages, NamedMasterService

_user_type_master = NamedMasterService[
    models.UserType,
    schemas.user_type.UserTypeCreate,
    schemas.user_type.UserTypeUpdate,
](
    crud=crud.user_type,
    get_by_name=lambda db, name: crud.user_type.get_by_name(db, name=name),
    get_id=lambda user_type: int(user_type.id),
    messages=NamedMasterMessages(
        required_name="社員種別名を入力してください",
        duplicate_create="この社員種別名は既に存在します",
        duplicate_update="この社員種別名は既に使用されています",
        delete_integrity="利用中の社員種別は削除できません",
    ),
)


def validate_user_type_creation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> None:
    """作成前に社員種別名を検証する。

    Args:
        db: DB session。
        user_type_in: 作成予定の社員種別データ。

    Raises:
        HTTPException: 名称が空または重複する場合。
    """
    _user_type_master.validate_creation(db, name=user_type_in.name)


def validate_user_type_update(
    db: Session,
    *,
    user_type_id_to_update: int,
    user_type_in: schemas.user_type.UserTypeUpdate,
) -> None:
    """更新対象自身を除外して社員種別名を検証する。

    Args:
        db: DB session。
        user_type_id_to_update: 更新対象の社員種別ID。
        user_type_in: 更新予定の社員種別データ。

    Raises:
        HTTPException: 名称が空または別entityと重複する場合。
    """
    _user_type_master.validate_update(
        db,
        object_id=user_type_id_to_update,
        name=user_type_in.name,
    )


def create_user_type_with_validation(
    db: Session, *, user_type_in: schemas.user_type.UserTypeCreate
) -> models.UserType:
    """社員種別を検証して1 transactionで作成する。

    Args:
        db: DB session。
        user_type_in: 作成する社員種別データ。

    Returns:
        作成後の社員種別model。

    Raises:
        HTTPException: 名称validationに失敗した場合。
        ApplicationError: DB integrity conflictが発生した場合。
    """
    return _user_type_master.create(db, obj_in=user_type_in, name=user_type_in.name)


def update_user_type_with_validation(
    db: Session, *, user_type_id: int, user_type_in: schemas.user_type.UserTypeUpdate
) -> models.UserType:
    """既存社員種別を検証して1 transactionで更新する。

    Args:
        db: DB session。
        user_type_id: 更新対象の社員種別ID。
        user_type_in: 更新内容。

    Returns:
        更新後の社員種別model。

    Raises:
        HTTPException: 対象不在または名称validationに失敗した場合。
        ApplicationError: DB integrity conflictが発生した場合。
    """
    return _user_type_master.update(
        db,
        object_id=user_type_id,
        obj_in=user_type_in,
        name=user_type_in.name,
    )


def delete_user_type(db: Session, *, user_type_id: int) -> models.UserType:
    """未使用社員種別を削除する。

    Args:
        db: DB session。
        user_type_id: 削除対象の社員種別ID。

    Returns:
        削除した社員種別model。

    Raises:
        HTTPException: 対象が存在しない場合。
        ApplicationError: DB参照制約等により削除できない場合。
    """
    return _user_type_master.delete(db, object_id=user_type_id)
