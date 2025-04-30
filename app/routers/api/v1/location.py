"""
勤務場所APIエンドポイント
=====================

勤務場所の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.crud.location import location
from app.db.session import get_db
from app.schemas.location import Location, LocationCreate, LocationList, LocationUpdate

# サービス層をインポート
from app.services import location_service

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
    サービス層でバリデーションを実行します。
    """
    # バリデーションと作成をサービス層に委譲
    return location_service.create_location_with_validation(
        db=db, location_in=location_in
    )


@router.put("/{location_id}", response_model=Location)
def update_location(
    *,
    db: Session = Depends(get_db),
    location_id: int,
    location_in: LocationUpdate,
) -> Any:
    """
    勤務場所を更新します。
    サービス層でバリデーションを実行します。
    """
    # バリデーションと更新をサービス層に委譲
    return location_service.update_location_with_validation(
        db=db, location_id=location_id, location_in=location_in
    )


@router.delete("/{location_id}")
def delete_location(*, db: Session = Depends(get_db), location_id: int) -> Any:
    """
    勤務場所を削除します。
    """
    location_obj = location.get_or_404(db=db, id=location_id)
    
    # 削除しようとしている勤務場所が現在勤怠データで使用されていないか確認します。
    # attendance_count = db.query(Attendance).filter(Attendance.location_id == location_id).count()
    # if attendance_count > 0:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"この勤務場所は{attendance_count}件の勤怠データで使用されているため削除できません"
    #     )
    # ↑ このチェックは crud.location.remove 内に移動

    location.remove(db=db, id=location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 