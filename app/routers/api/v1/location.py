"""
勤務場所APIエンドポイント
=====================

勤務場所の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.location import location
from app.db.session import get_db
from app.models.attendance import Attendance
from app.schemas.location import Location, LocationCreate, LocationList, LocationUpdate

router = APIRouter(tags=["Locations"])


@router.get("", response_model=LocationList)
def get_locations(db: Session = Depends(get_db)) -> Any:
    """
    全ての勤務場所を取得します。名前順でソートされます。
    """
    locations = db.query(location.model).order_by(location.model.name).all()
    return {"locations": locations}


@router.post("", response_model=Location)
def create_location(
    *, db: Session = Depends(get_db), location_in: LocationCreate
) -> Any:
    """
    新しい勤務場所を作成します。
    """
    if not location_in.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="勤務場所名を入力してください",
        )
    
    existing_location = location.get_by_name(db, name=location_in.name)
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この勤務場所は既に存在します",
        )
    
    return location.create(db=db, obj_in=location_in)


@router.put("/{location_id}", response_model=Location)
def update_location(
    *,
    db: Session = Depends(get_db),
    location_id: int,
    location_in: LocationUpdate,
) -> Any:
    """
    勤務場所を更新します。
    """
    location_obj = location.get_by_id(db=db, location_id=location_id)
    if not location_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="勤務場所が見つかりません"
        )
    
    # 新しい名前が指定され、かつ現在の名前と異なる場合に重複チェックを行います。
    if location_in.name and location_in.name != location_obj.name:
        existing = location.get_by_name(db, name=location_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この勤務場所名は既に使用されています",
            )
    
    return location.update(db=db, db_obj=location_obj, obj_in=location_in)


@router.delete("/{location_id}")
def delete_location(*, db: Session = Depends(get_db), location_id: int) -> Any:
    """
    勤務場所を削除します。
    """
    location_obj = location.get_by_id(db=db, location_id=location_id)
    if not location_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="勤務場所が見つかりません"
        )
    
    # 削除しようとしている勤務場所が現在勤怠データで使用されていないか確認します。
    attendance_count = db.query(Attendance).filter(Attendance.location_id == location_id).count()
    if attendance_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"この勤務場所は{attendance_count}件の勤怠データで使用されているため削除できません"
        )

    location.remove(db=db, id=location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 