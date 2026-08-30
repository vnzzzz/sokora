"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.db.session import get_db
from app.crud.attendance import attendance
from app.crud.location import location
from app.schemas.attendance import Attendance, AttendanceCreate, AttendanceList, AttendanceUpdate, UserAttendance
from app.core.config import logger

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
def get_user_attendance(
    user_id: str, 
    date: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    特定ユーザーの勤怠データを取得します。
    date パラメータを指定すると、特定日の勤怠データのみを返します。
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
        entry_date = entry["date"]
        
        # dateパラメータが指定されている場合は、その日のデータのみをフィルタリング
        if date and entry_date != date:
            continue
            
        entry_data = {
            "date": entry_date,
            "location_id": entry["location_id"],
            "location": entry["location_name"]
        }
        
        # attendance_idが存在する場合は追加
        if "id" in entry:
            entry_data["attendance_id"] = entry["id"]
            
        dates.append(entry_data)
    
    # dateパラメータが指定されていて、日付が見つからなかった場合
    if date and not dates:
        # キーは揃えておく
        return {
            "user_id": user_id,
            "user_name": user_name,
            "dates": []
        }
    
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
        return {"success": True, "data": {}}
    return {"success": True, "data": detail}


@router.post("")
async def create_attendance(
    request: Request,
    user_id: str = Form(...),
    date: str = Form(...),
    location_id: int = Form(...),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    勤怠データを作成します。
    """
    try:
        # 勤務場所IDの確認
        if location_id != -1:  # -1は削除用特殊値
            loc = location.get_by_id(db, location_id=location_id)
            if not loc:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "message": f"勤務場所ID '{location_id}' が見つかりません"}
                )
        
        success = attendance.update_user_entry(
            db, user_id=user_id, date_str=date, location_id=location_id
        )
        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "勤怠データの作成に失敗しました。ユーザーIDまたは日付が無効である可能性があります。"}
            )
        
        # 作成したデータを返す
        from app.crud.user import user
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": f"ユーザー '{user_id}' が見つかりません"}
            )
        
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        attendance_obj = attendance.get_by_user_and_date(db, user_id=str(user_obj.user_id), date=date_obj)
        
        if attendance_obj is None and location_id != -1:
            # 削除でなく、かつオブジェクトが見つからない場合はエラー
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "message": "勤怠データは更新されましたが、取得できませんでした"}
            )
        
        # 削除操作の場合は成功メッセージを返す
        if location_id == -1:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "message": "勤怠データを正常に削除しました"}
            )
        
        # 常に成功レスポンスを返す（HTMLリクエストとAPIリクエストで共通）
        # attendance_objはPydanticモデルに変換されていないため、JSONに変換可能なデータを返す
        if attendance_obj is not None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True, 
                    "message": "勤怠データを正常に登録しました",
                    "data": {
                        "id": attendance_obj.id,
                        "user_id": attendance_obj.user_id,
                        "date": attendance_obj.date.isoformat(),
                        "location_id": attendance_obj.location_id
                    }
                }
            )
        else:
            # データが見つからない場合でも成功として返す
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True, 
                    "message": "勤怠データを正常に登録しました",
                    "data": None
                }
            )
    except Exception as e:
        logger.error(f"勤怠作成エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"勤怠データの作成中にエラーが発生しました: {str(e)}"}
        )


@router.put("/{attendance_id}")
async def update_attendance(
    request: Request,
    attendance_id: int,
    location_id: int = Form(...),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    勤怠データを更新します。
    """
    try:
        attendance_obj = attendance.get(db=db, id=attendance_id)
        if not attendance_obj:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "勤怠データが見つかりません"}
            )
        
        if location_id == -1:  # 削除用特殊値
            try:
                # 削除処理
                attendance.remove(db=db, id=attendance_id)
                db.commit()
                logger.debug(f"勤怠ID {attendance_id} の削除に成功しました")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"success": True, "message": "勤怠データを正常に削除しました"}
                )
            except Exception as e:
                db.rollback()
                logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"success": False, "message": f"勤怠データの削除中にエラーが発生しました: {str(e)}"}
                )
        else:
            # 勤務場所IDの確認
            loc = location.get_by_id(db, location_id=location_id)
            if not loc:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "message": f"勤務場所ID '{location_id}' が見つかりません"}
                )
                
            try:
                # 更新処理
                attendance_update = AttendanceUpdate(location_id=location_id)
                updated_obj = attendance.update(db=db, db_obj=attendance_obj, obj_in=attendance_update)
                db.commit()
                logger.debug(f"勤怠ID {attendance_id} の更新に成功しました")
                
                if updated_obj is not None:
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "success": True, 
                            "message": "勤怠データを正常に更新しました",
                            "data": {
                                "id": updated_obj.id,
                                "user_id": updated_obj.user_id,
                                "date": updated_obj.date.isoformat(),
                                "location_id": updated_obj.location_id
                            }
                        }
                    )
                else:
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "success": True, 
                            "message": "勤怠データを正常に更新しました",
                            "data": None
                        }
                    )
            except Exception as e:
                db.rollback()
                logger.error(f"勤怠更新エラー: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"success": False, "message": f"勤怠データの更新中にエラーが発生しました: {str(e)}"}
                )
    except Exception as e:
        logger.error(f"勤怠更新エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"勤怠データの更新中にエラーが発生しました: {str(e)}"}
        )


@router.delete("/{attendance_id}")
async def delete_attendance(
    request: Request,
    attendance_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    勤怠データを削除します。
    """
    try:
        attendance_obj = attendance.get(db=db, id=attendance_id)
        if not attendance_obj:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "勤怠データが見つかりません"}
            )
        
        try:
            attendance.remove(db=db, id=attendance_id)
            db.commit()
            logger.debug(f"勤怠ID {attendance_id} の削除に成功しました")
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "message": "勤怠データを正常に削除しました"}
            )
        except Exception as e:
            db.rollback()
            logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "message": f"勤怠データの削除中にエラーが発生しました: {str(e)}"}
            )
    except Exception as e:
        logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"勤怠データの削除中にエラーが発生しました: {str(e)}"}
        )
