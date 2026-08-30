"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.user import user
from app.crud.attendance import attendance
from app.db.session import get_db
from app.schemas.user import User, UserCreate, UserList, UserUpdate
from app.services import user_service # サービス層をインポート

# API用ルーター
router = APIRouter(tags=["Users"])


@router.get("", response_model=UserList)
def get_users(db: Session = Depends(get_db)) -> Any:
    """
    全てのユーザーを取得します。
    """
    users_data = user.get_all_users(db)
    users_list = []
    
    for user_name, user_id_str, user_type_id in users_data:
        user_obj = user.get(db, id=user_id_str)
        if user_obj:
            users_list.append(user_obj)
    
    return {"users": users_list}


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)) -> Any:
    """
    指定したIDのユーザーを取得します。
    """
    user_obj = user.get_or_404(db, id=user_id)
    return user_obj


@router.post("", response_model=User)
async def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    新しいユーザーを作成します。
    """
    # サービス層の関数を呼び出してユーザーを作成
    # バリデーションはサービス層で行われる
    return user_service.create_user_with_validation(db=db, user_in=user_in)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
) -> Any:
    """
    ユーザー情報を更新します。
    """
    # サービス層の関数を呼び出してユーザーを更新
    # バリデーションとユーザー存在確認はサービス層で行われる
    return user_service.update_user_with_validation(
        db=db, user_id=user_id, user_in=user_in
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str, 
    db: Session = Depends(get_db)
) -> Any:
    """
    ユーザーを削除します。
    """
    try:
        user_obj = user.get_or_404(db, id=user_id)
            
        # 先に関連する勤怠データを削除
        attendance.delete_attendances_by_user_id(db=db, user_id=user_id)
            
        # ユーザーを削除
        user.remove(db, id=user_id)
        
        db.commit() # 勤怠削除とユーザー削除をコミット
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        db.rollback() # エラー時はロールバック
        raise
    except Exception as e:
        db.rollback() # エラー時はロールバック
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) 