"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.user import user
from app.crud.group import group
from app.crud.user_type import user_type
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
        user_obj = user.get_by_user_id(db, user_id=user_id_str)
        if user_obj:
            users_list.append(user_obj)
    
    return {"users": users_list}


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)) -> Any:
    """
    指定したIDのユーザーを取得します。
    """
    user_obj = user.get_by_user_id(db, user_id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"ユーザー '{user_id}' が見つかりません"
        )
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
        # グループIDを整数型に変換
        try:
            group_id_int = int(user_in.group_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なグループIDが指定されました"
            )
            
        # グループ存在確認
        group_obj = group.get_by_id(db, group_id=group_id_int)
        if not group_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"グループID '{group_id_int}' が存在しません"
            )
        
        # 社員種別IDを整数型に変換
        try:
            user_type_id_int = int(user_in.user_type_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な社員種別IDが指定されました"
            )
            
        # 社員種別存在確認
        user_type_obj = user_type.get_by_id(db, user_type_id=user_type_id_int)
        if not user_type_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"社員種別ID '{user_type_id_int}' が存在しません"
            )
                
        # UserCreateオブジェクトを作成
        user_data = {
            "username": user_in.username,
            "user_id": user_in.user_id,
            "group_id": group_id_int,
            "user_type_id": user_type_id_int
        }
        
        # 既存ユーザーチェックと新規作成
        existing_user = user.get_by_user_id(db, user_id=user_in.user_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このユーザーIDは既に使用されています"
            )
            
        # ユーザーを作成
        user_obj = user.create_with_id(db, obj_in=user_data)
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
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"ユーザー '{user_id}' が見つかりません"
            )
            
        # グループIDを整数型に変換
        try:
            group_id_int = int(user_in.group_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なグループIDが指定されました"
            )
        
        # グループ存在確認
        group_obj = group.get_by_id(db, group_id=group_id_int)
        if not group_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"グループID '{group_id_int}' が存在しません"
            )
        
        # 社員種別IDを整数型に変換
        try:
            user_type_id_int = int(user_in.user_type_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な社員種別IDが指定されました"
            )
            
        # 社員種別存在確認
        user_type_obj = user_type.get_by_id(db, user_type_id=user_type_id_int)
        if not user_type_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"社員種別ID '{user_type_id_int}' が存在しません"
            )
        
        success = user.update_user(
            db, 
            user_id=user_id, 
            username=user_in.username, 
            group_id=group_id_int,
            user_type_id=user_type_id_int
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ユーザー '{user_id}' の更新に失敗しました。"
            )
        return user.get_by_user_id(db, user_id=user_id)
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
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"ユーザー '{user_id}' が見つかりません"
            )
            
        user.delete_user(db, user_id=user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) 