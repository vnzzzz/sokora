"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.db.session import get_db
from app.crud.attendance import attendance
from app.crud.location import location
from app.schemas.attendance import Attendance, AttendanceCreate, AttendanceList, AttendanceUpdate, UserAttendance

# API用ルーター
router = APIRouter(tags=["Attendance"])


@router.get("", response_model=AttendanceList)
def get_attendances(db: Session = Depends(get_db)) -> Any:
    """
    全ての勤怠データを取得します。
    """
    attendances = db.query(attendance.model).all()
    return {"records": attendances}


@router.get("/user/{user_id}", response_model=UserAttendance)
def get_user_attendance(user_id: str, db: Session = Depends(get_db)) -> Any:
    """
    特定ユーザーの勤怠データを取得します。
    """
    from app.crud.user import user
    
    user_obj = user.get_by_user_id(db, user_id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"ユーザー '{user_id}' が見つかりません"
        )
    
    user_entries = attendance.get_user_data(db, user_id=user_id)
    user_name = user.get_user_name_by_id(db, user_id=user_id)
    
    # UserAttendanceスキーマに合わせてデータを整形
    dates = []
    for entry in user_entries:
        entry_data = {
            "date": entry["date"],
            "location_id": entry["location_id"],
            "location": entry["location_name"]
        }
        
        # attendance_idが存在する場合は追加
        if "id" in entry:
            entry_data["attendance_id"] = entry["id"]
            
        dates.append(entry_data)
    
    return {
        "user_id": user_id,
        "user_name": user_name,
        "dates": dates
    }


@router.get("/day/{day}")
def get_day_attendance(day: str, db: Session = Depends(get_db)) -> Any:
    """
    指定した日の全ユーザーの勤怠データを取得します。
    """
    detail = attendance.get_day_data(db, day=day)
    if not detail:
        return {}
    return detail


@router.post("", response_model=Attendance)
async def create_attendance(
    user_id: str = Form(...),
    date: str = Form(...),
    location_id: int = Form(...),
    db: Session = Depends(get_db),
) -> Any:
    """
    勤怠データを作成します。
    """
    try:
        # 勤務場所IDの確認
        if location_id != -1:  # -1は削除用特殊値
            loc = location.get_by_id(db, location_id=location_id)
            if not loc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"勤務場所ID '{location_id}' が見つかりません"
                )
        
        success = attendance.update_user_entry(
            db, user_id=user_id, date_str=date, location_id=location_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="勤怠データの作成に失敗しました。ユーザーIDまたは日付が無効である可能性があります。"
            )
        
        # 作成したデータを返す
        from app.crud.user import user
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"ユーザー '{user_id}' が見つかりません"
            )
        
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        attendance_obj = attendance.get_by_user_and_date(db, user_id=str(user_obj.user_id), date=date_obj)
        
        return attendance_obj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{attendance_id}", response_model=Attendance)
async def update_attendance(
    attendance_id: int,
    location_id: int = Form(...),
    db: Session = Depends(get_db),
) -> Any:
    """
    勤怠データを更新します。
    """
    try:
        attendance_obj = attendance.get(db=db, id=attendance_id)
        if not attendance_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="勤怠データが見つかりません"
            )
        
        if location_id == -1:  # 削除用特殊値
            # 削除の場合はDeleteエンドポイントへのリダイレクト
            attendance.remove(db=db, id=attendance_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        else:
            # 勤務場所IDの確認
            loc = location.get_by_id(db, location_id=location_id)
            if not loc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"勤務場所ID '{location_id}' が見つかりません"
                )
                
            # 更新
            attendance_update = AttendanceUpdate(location_id=location_id)
            return attendance.update(db=db, db_obj=attendance_obj, obj_in=attendance_update)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{attendance_id}")
async def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """
    勤怠データを削除します。
    """
    try:
        attendance_obj = attendance.get(db=db, id=attendance_id)
        if not attendance_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="勤怠データが見つかりません"
            )
        
        attendance.remove(db=db, id=attendance_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
