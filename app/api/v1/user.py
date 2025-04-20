"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user
from ...schemas.user import User, UserCreate, UserList, UserUpdate

# API用ルーター
router = APIRouter(tags=["Users"])


@router.get("/", response_model=UserList)
def get_users(db: Session = Depends(get_db)) -> Any:
    """
    全てのユーザーを取得します。
    """
    users_data = user.get_all_users(db)
    users_list = []
    
    for user_name, user_id_str in users_data:
        user_obj = user.get_by_user_id(db, user_id=user_id_str)
        if user_obj:
            users_list.append(user_obj)
    
    return {"users": users_list}


@router.post("/", response_model=User)
async def create_user(
    username: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
) -> Any:
    """
    新しいユーザーを作成します。
    """
    try:
        # create_userメソッドはbooleanを返すので、成功した場合にUserオブジェクトを取得して返す
        success = user.create_user(db, username=username, user_id=user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ユーザーの作成に失敗しました。IDが既に使用されている可能性があります。"
            )
        
        # 作成したユーザーオブジェクトを取得して返す
        created_user = user.get_by_user_id(db, user_id=user_id)
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ユーザーは作成されましたが、取得できませんでした。"
            )
        
        return created_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    username: str = Form(...),
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
            
        success = user.update_user(db, user_id=user_id, username=username)
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