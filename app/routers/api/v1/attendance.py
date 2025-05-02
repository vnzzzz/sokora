"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from datetime import date, datetime
from typing import Any, Optional
import json # json をインポート

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, Response
from fastapi.responses import JSONResponse
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
    user_obj = user.get(db, id=user_id)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザー '{user_id}' が見つかりません"
        )

    user_entries = attendance.get_user_data(db, user_id=user_id)
    user_name = user.get_username_by_id(db, id=user_id)

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


@router.post("", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def create_attendance(
    user_id: str = Form(...),
    date_str: str = Form(..., alias="date"),
    location_id: int = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    """
    勤怠データを作成します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    """
    try:
        # 文字列から date オブジェクトへの変換
        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="日付の形式が無効です。YYYY-MM-DD形式で入力してください。"
            )

        # ユーザーと勤務場所の存在確認
        user.get_or_404(db, id=user_id)
        location.get_or_404(db, id=location_id)

        # 既存レコードのチェック
        existing_attendance = attendance.get_by_user_and_date(
            db, user_id=user_id, date=attendance_date
        )
        if existing_attendance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ユーザー '{user_id}' の日付 '{date_str}' には既に勤怠データが存在します。"
            )

        # AttendanceCreateオブジェクトを手動で作成
        attendance_in = AttendanceCreate(user_id=user_id, date=attendance_date, location_id=location_id)

        # 勤怠データ作成
        created_attendance = attendance.create(db=db, obj_in=attendance_in) # 作成されたオブジェクトを取得
        trigger_data = {
            "closeModal": f"attendance-modal-{user_id}-{date_str}",
            "refreshAttendance": None
        }
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)} # JSON文字列にする
        )

    except HTTPException:
        raise # HTTPExceptionはそのまま再送出
    except Exception as e:
        logger.error(f"勤怠作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"勤怠データの作成中にエラーが発生しました: {str(e)}"
        )


@router.put("/{attendance_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def update_attendance(
    attendance_id: int,
    attendance_in: AttendanceUpdate,
    db: Session = Depends(get_db),
) -> Response:
    """
    勤怠データを更新します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    """
    try:
        attendance_obj = attendance.get_or_404(db=db, id=attendance_id)
        
        # 新しい勤務場所IDの存在確認
        if attendance_in.location_id is not None:
            location.get_or_404(db, id=attendance_in.location_id)
                
        # 更新処理
        updated_obj = attendance.update(db=db, db_obj=attendance_obj, obj_in=attendance_in) # 更新後のオブジェクト取得
        logger.debug(f"勤怠ID {attendance_id} の更新に成功しました")
        trigger_data = {
            "closeModal": f"attendance-modal-{updated_obj.user_id}-{updated_obj.date.isoformat()}", # 更新後のオブジェクトから取得
            "refreshAttendance": None
        }
        logger.info(f"Sending HX-Trigger for modal close: {json.dumps(trigger_data)}")
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)}
        )

    except HTTPException:
        raise # HTTPExceptionはそのまま再送出
    except Exception as e:
        db.rollback() # update内でエラーがあればrollbackされるはずだが念のため
        logger.error(f"勤怠更新エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"勤怠データの更新中にエラーが発生しました: {str(e)}"
        )


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    request: Request,
    attendance_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """
    勤怠データを削除します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    """
    try:
        # get_or_404 は HTTPException を送出する可能性がある
        attendance_obj = attendance.get_or_404(db=db, id=attendance_id)
        
        # ここに到達すればオブジェクトは存在する
        # try:
        #     attendance.remove(db=db, id=attendance_id)
        #     db.commit()
        #     logger.debug(f"勤怠ID {attendance_id} の削除に成功しました")
            
        #     return JSONResponse(
        #         status_code=status.HTTP_200_OK,
        #         content={"success": True, "message": "勤怠データを正常に削除しました"}
        #     )
        # except Exception as e:
        #     db.rollback()
        #     logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
        #     return JSONResponse(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         content={"success": False, "message": f"勤怠データの削除中にエラーが発生しました: {str(e)}"}
        #     )
        
        # remove処理自体はシンプルなので、内側のtry-exceptは不要かもしれない
        attendance.remove(db=db, id=attendance_id) # removeは内部でcommitしない想定 (base.py次第)
        # db.commit() # removeがcommitしない場合、ここでcommitが必要。base.pyを確認。
        logger.debug(f"勤怠ID {attendance_id} の削除に成功しました")
        user_id_deleted = attendance_obj.user_id # 削除前に取得
        date_deleted = attendance_obj.date.isoformat() # 削除前に取得
        trigger_data = {
            "closeModal": f"attendance-modal-{user_id_deleted}-{date_deleted}",
            "refreshAttendance": None
        }
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)}
        )

    except HTTPException as http_exc:
        # get_or_404 が発生させた 404 エラーをそのまま返す
        raise http_exc
    except Exception as e:
        # その他の予期せぬエラー
        db.rollback() # 念のためロールバック
        logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"勤怠データの削除中にエラーが発生しました: {str(e)}"
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_user_date(
    user_id: str,
    date: date, # FastAPIが "YYYY-MM-DD" から date オブジェクトに変換
    db: Session = Depends(get_db),
) -> Response:
    """
    ユーザーIDと日付を指定して勤怠データを削除します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    """
    logger.info(f"ユーザーIDと日付による勤怠削除開始: User={user_id}, Date={date}")
    deleted = attendance.delete_by_user_and_date(db=db, user_id=user_id, date_obj=date)
    if not deleted:
        # 削除対象が見つからなくてもエラーとはせず、404を返す
        logger.warning(f"削除対象の勤怠データが見つかりません: User={user_id}, Date={date}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="対象の勤怠データが見つかりません")

    db.commit() # delete_by_user_and_date が commit しないため、ここで commit
    logger.info(f"ユーザーIDと日付による勤怠削除成功: User={user_id}, Date={date}")
    trigger_data = {
        "closeModal": f"attendance-modal-{user_id}-{date.isoformat()}", # 引数の date を使う
        "refreshAttendance": None
    }
    return Response(
        content="",
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Trigger": json.dumps(trigger_data)}
    )
