"""
勤怠種別APIエンドポイント
=====================

勤怠種別の取得、作成、更新、削除のためのAPIエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud.location import location
from app.db.session import get_db
from app.schemas.location import Location, LocationCreate, LocationList, LocationUpdate
from app.services import location_service

router = APIRouter(tags=["Locations"])


@router.get("", response_model=LocationList)
def get_locations(db: Session = Depends(get_db)) -> Any:
    """勤怠種別一覧を名前順で返す。

    Args:
        db: DB session。

    Returns:
        `locations`に勤怠種別一覧を格納したmapping。
    """
    locations = db.query(location.model).order_by(location.model.name).all()
    return {"locations": locations}


@router.post("", response_model=Location)
def create_location(
    *, db: Session = Depends(get_db), location_in: LocationCreate
) -> Any:
    """入力を検証して勤怠種別を作成する。

    Args:
        db: DB session。
        location_in: 作成する勤怠種別データ。

    Returns:
        作成後の勤怠種別。

    Raises:
        HTTPException: 名前等の入力が不正または重複する場合。
    """
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
    """指定IDの勤怠種別を検証して更新する。

    Args:
        db: DB session。
        location_id: 更新対象の勤怠種別ID。
        location_in: 更新内容。

    Returns:
        更新後の勤怠種別。

    Raises:
        HTTPException: 対象が存在しない、または入力が不正/重複する場合。
    """
    return location_service.update_location_with_validation(
        db=db, location_id=location_id, location_in=location_in
    )


@router.delete("/{location_id}")
def delete_location(*, db: Session = Depends(get_db), location_id: int) -> Any:
    """指定IDの未使用勤怠種別を削除する。

    Args:
        db: DB session。
        location_id: 削除対象の勤怠種別ID。

    Returns:
        bodyなしの204 response。

    Raises:
        HTTPException: 対象が存在しない、または参照中で削除できない場合。
    """
    location_service.delete_location(db=db, location_id=location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
