import pytest
from sqlalchemy.orm import Session

from app import crud
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from app.models import Group as GroupModel, UserType as UserTypeModel
from app.schemas.group import GroupCreate
from app.schemas.user_type import UserTypeCreate
from app.tests.utils.utils import random_lower_string, random_email

# pytestmark = pytest.mark.asyncio # CRUD操作は同期的であるため不要


@pytest.fixture(scope="function")
def db_with_data(db: Session) -> Session:
    """テストに必要な基本データを投入したDBセッション"""
    # Group を作成
    group_in = GroupCreate(name="Test Group")
    group = crud.group.create(db=db, obj_in=group_in)
    # UserType を作成
    user_type_in = UserTypeCreate(name="Test Type")
    user_type = crud.user_type.create(db=db, obj_in=user_type_in)

    # このフィクスチャ内では User は作成しない
    # User 作成は各テストケース、またはそれを必要とするフィクスチャで行う

    # db.commit() # function スコープの場合、commit せずに Session を返せばテスト後に rollback される
    return db


def test_create_user(db_with_data: Session) -> None:
    """新しいユーザーを作成するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Test User Name"
    # 関連データのIDを取得
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    assert group and user_type # 前提条件の確認

    user_in = UserCreate(
        user_id=user_id,
        username=username,
        group_id=int(group.id),
        user_type_id=int(user_type.id)
    )
    # CRUDBase.create は obj_in のみ受け付ける
    user = crud.user.create(db=db, obj_in=user_in)
    assert user.id == user_id
    assert user.username == username
    assert user.group_id == group.id
    assert user.user_type_id == user_type.id
    # email, hashed_password, full_name などがデフォルトで設定されるか、
    # または他のメソッドで設定されることを期待
    # assert hasattr(user, "hashed_password")
    # assert user.email is not None
    # assert user.full_name is not None


def test_get_user(db_with_data: Session) -> None:
    """IDでユーザーを取得するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Get Test User"
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    assert group and user_type

    user_in = UserCreate(
        user_id=user_id, username=username, group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user = crud.user.create(db=db, obj_in=user_in)
    # get のテスト
    user_2 = crud.user.get(db=db, id=user.id)
    assert user_2
    assert user.id == user_2.id
    assert user.username == user_2.username
    # email, full_name などはcreate時に設定されていない可能性
    # assert user.email == user_2.email
    # assert user.full_name == user_2.full_name


def test_update_user(db_with_data: Session) -> None:
    """ユーザー情報を更新するテスト"""
    db = db_with_data
    user_id = random_lower_string(8)
    username = "Update User"
    group = db.query(GroupModel).filter(GroupModel.name == "Test Group").first()
    user_type = db.query(UserTypeModel).filter(UserTypeModel.name == "Test Type").first()
    assert group and user_type

    user_in = UserCreate(
        user_id=user_id, username=username, group_id=int(group.id), user_type_id=int(user_type.id)
    )
    user = crud.user.create(db=db, obj_in=user_in)

    new_username = "Updated User Name"
    new_group_in = GroupCreate(name="New Test Group")
    new_group = crud.group.create(db=db, obj_in=new_group_in)
    new_user_type_in = UserTypeCreate(name="New Test Type")
    new_user_type = crud.user_type.create(db=db, obj_in=new_user_type_in)
    db.commit()

    user_in_update = UserUpdate(username=new_username, group_id=int(new_group.id), user_type_id=int(new_user_type.id))

    # update を実行
    updated_user_instance = crud.user.update(db=db, db_obj=user, obj_in=user_in_update)
    # update 後に commit を追加
    db.commit()

    # 更新後にDBから再取得して検証
    user_updated_from_db = crud.user.get(db=db, id=user.id)

    assert user_updated_from_db is not None
    assert user_updated_from_db.id == user_id
    assert user_updated_from_db.username == new_username
    assert user_updated_from_db.group_id == new_group.id
    assert user_updated_from_db.user_type_id == new_user_type.id

# authenticate, is_active, is_superuser は User モデルに email, password, is_active, is_superuser
# フィールドが設定されている必要がある。現状の create では設定できないため、テスト不能。
# これらのテストは、Userモデルの作成方法（または更新方法）が明確になってから実装する。

# def test_authenticate_user(db_with_data: Session) -> None:
#     """ユーザー認証をテストする"""
#     ...
# def test_is_active(db_with_data: Session) -> None:
#     """ユーザーがアクティブかどうかのテスト"""
#     ...
# def test_is_superuser(db_with_data: Session) -> None:
#     """ユーザーがスーパーユーザーかどうかのテスト"""
#     ... 