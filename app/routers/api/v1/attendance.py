"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.user import user
from app.db.session import get_db
from app.schemas.attendance import (
    Attendance,
    AttendanceCreate,
    AttendanceList,
    AttendanceUpdate,
    UserAttendance,
)

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
    user_obj = user.get_by_user_id(db, user_id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザー '{user_id}' が見つかりません"
        )

    user_entries = attendance.get_user_data(db, user_id=user_id)
    user_name = user.get_user_name_by_id(db, user_id=user_id)

    # 取得したデータをレスポンススキーマ形式に整形します。
    dates = []
    for entry in user_entries:
        entry_date = entry["date"]

        # dateパラメータが指定されている場合、一致する日付のデータのみを抽出します。
        if date and entry_date != date:
            continue

        entry_data = {
            "date": entry_date,
            "location_id": entry["location_id"],
            "location": entry["location_name"]
        }

        # 勤怠レコードID (attendance_id) が存在すればレスポンスに含めます。
        if "id" in entry:
            entry_data["attendance_id"] = entry["id"]

        dates.append(entry_data)

    # dateパラメータが指定され、かつ該当日のデータが見つからなかった場合の処理。
    if date and not dates:
        # レスポンスの構造を維持するため、空のdatesリストを含むデータを返します。
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


@router.delete("", status_code=status.HTTP_200_OK)
def delete_attendance_by_user_date(
    user_id: str,
    date: date, # FastAPIが "YYYY-MM-DD" から date オブジェクトに変換
    db: Session = Depends(get_db),
) -> JSONResponse:
    """指定されたユーザーと日付の勤怠データを削除します。"""
    try:
        logger.debug(f"勤怠削除リクエスト受信: user_id={user_id}, date={date}")
        
        # ユーザーの存在確認 (任意ですが、より親切)
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"ユーザー '{user_id}' が見つかりません"
            )
        
        # CRUD関数を呼び出して削除
        deleted = attendance.delete_by_user_and_date(db=db, user_id=user_id, date_obj=date)
        
        if deleted:
            db.commit()
            logger.info(f"勤怠データ削除成功: user_id={user_id}, date={date}")
            return JSONResponse(
                content={"success": True, "message": "勤怠データを正常に削除しました"}
            )
        else:
            # 削除対象が見つからなかった場合もエラーではないとする
            logger.warning(f"削除対象の勤怠データが見つかりませんでした: user_id={user_id}, date={date}")
            return JSONResponse(
                content={"success": True, "message": "削除対象のデータが見つかりませんでした"}
            )
            
    except HTTPException as http_exc:
        # HTTP関連のエラーはそのまま再raise
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"勤怠削除中に予期せぬエラー: user_id={user_id}, date={date}, error={str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"勤怠データの削除中にエラーが発生しました: {str(e)}"}
        )
