"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.group import group
from app.crud.user import user
from app.crud.user_type import user_type
from app.crud.attendance import attendance
from app.db.session import get_db
from app.schemas.user import User, UserCreate, UserList, UserUpdate

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
    try:
        # 入力されたグループIDを整数に変換し、存在を確認します。
        try:
            group_id_int = int(user_in.group_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なグループIDが指定されました"
            )

        group_obj = group.get_or_404(db, id=group_id_int)

        # 入力された社員種別IDを整数に変換し、存在を確認します。
        try:
            user_type_id_int = int(user_in.user_type_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な社員種別IDが指定されました"
            )

        user_type_obj = user_type.get_or_404(db, id=user_type_id_int)

        # 指定されたユーザーIDが既に存在するか確認します。
        existing_user = user.get(db, id=user_in.id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このユーザーIDは既に使用されています"
            )

        # ユーザーを作成します。
        user_obj = user.create(db, obj_in=user_in)
        return user_obj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
) -> Any:
    """
    ユーザー情報を更新します。
    """
    try:
        user_obj = user.get_or_404(db, id=user_id)
            
        # 入力されたグループIDを整数に変換し、存在を確認します。
        try:
            group_id_int = int(user_in.group_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なグループIDが指定されました"
            )
        
        group_obj = group.get_or_404(db, id=group_id_int)
        
        # 入力された社員種別IDを整数に変換し、存在を確認します。
        try:
            user_type_id_int = int(user_in.user_type_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な社員種別IDが指定されました"
            )
            
        user_type_obj = user_type.get_or_404(db, id=user_type_id_int)
        
        # ユーザー情報を更新します。
        updated_user = user.update(db=db, db_obj=user_obj, obj_in=user_in)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ユーザー '{user_id}' の更新に失敗しました。"
            )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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