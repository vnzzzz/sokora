"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from datetime import date, datetime, timedelta
from typing import Any, Optional, cast
import json # json をインポート
import re # 正規表現を追加

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, Response
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.user import user
from app.db.session import get_db
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceList,
    AttendanceUpdate,
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


@router.get("/day/{day}")
def get_day_attendance(day: str, db: Session = Depends(get_db)) -> Any:
    """
    指定した日の全ユーザーの勤怠データを取得します。
    """
    detail = attendance.get_day_data(db, day=day)
    if not detail:
        return {"success": True, "data": {}}
    return {"success": True, "data": detail}


# リクエストからmonth情報を抽出するヘルパー関数
def extract_month_from_request(request: Request) -> Optional[str]:
    """
    リクエストから現在表示中の月情報を抽出します。
    
    Args:
        request: FastAPIリクエストオブジェクト
        
    Returns:
        Optional[str]: 抽出された月情報 (YYYY-MM形式)、見つからない場合はNone
    """
    # Refererヘッダーからの抽出を試みる
    referer = request.headers.get("referer", "")
    month_match = re.search(r"month=([0-9]{4}-[0-9]{2})", referer)
    
    if month_match:
        return month_match.group(1)
    
    # X-Test-Monthヘッダー (テスト用)
    if "x-test-month" in request.headers:
        return request.headers.get("x-test-month")
    
    return None


def extract_week_from_request(request: Request, attendance_date: Optional[date] = None) -> Optional[str]:
    """
    リクエストから現在表示中の週情報を抽出します。

    Args:
        request: FastAPIリクエストオブジェクト
        attendance_date: 勤怠日付（リファラが無い場合のフォールバック用）

    Returns:
        Optional[str]: 抽出された週情報 (YYYY-MM-DD形式の月曜日)、見つからない場合はNone
    """
    referer = request.headers.get("referer", "")
    week_match = re.search(r"week=([0-9]{4}-[0-9]{2}-[0-9]{2})", referer)

    if week_match:
        return week_match.group(1)

    if "x-test-week" in request.headers:
        return request.headers.get("x-test-week")

    if attendance_date:
        monday = attendance_date - timedelta(days=attendance_date.weekday())
        return monday.isoformat()

    return None


@router.post("", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def create_attendance(
    request: Request,
    user_id: str = Form(...),
    date_str: str = Form(..., alias="date"),
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
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

        # ユーザーと勤怠種別の存在確認
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
        attendance_in = AttendanceCreate(user_id=user_id, date=attendance_date, location_id=location_id, note=note)

        # 勤怠データ作成
        attendance.create(db=db, obj_in=attendance_in)
        
        # 現在表示中の月/週情報を取得
        current_month = extract_month_from_request(request)
        current_week = extract_week_from_request(request, attendance_date)
        
        # トリガーデータを作成
        trigger_data = {
            "closeModal": f"attendance-modal-{user_id}-{date_str}",
            "refreshUserAttendance": {"user_id": user_id, "month": current_month, "week": current_week},
            "refreshAttendance": {"month": current_month, "week": current_week} # 月/週情報を含める
        }
        
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)}
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
    request: Request,
    attendance_id: int,
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Response:
    """
    勤怠データを更新します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    """
    try:
        attendance_obj = attendance.get_or_404(db=db, id=attendance_id)
        
        # 新しい勤怠種別IDの存在確認
        location.get_or_404(db, id=location_id)
        
        # 更新データを作成
        attendance_in = AttendanceUpdate(location_id=location_id, note=note)
                
        # 更新処理
        updated_obj = attendance.update(db=db, db_obj=attendance_obj, obj_in=attendance_in) # 更新後のオブジェクト取得
        logger.debug(f"勤怠ID {attendance_id} の更新に成功しました")
        
        # 現在表示中の月/週情報を取得
        current_month = extract_month_from_request(request)
        current_week = extract_week_from_request(request, cast(date, updated_obj.date))
        
        # トリガーデータを作成
        trigger_data = {
            "closeModal": f"attendance-modal-{updated_obj.user_id}-{updated_obj.date.isoformat()}",
            "refreshUserAttendance": {"user_id": updated_obj.user_id, "month": current_month, "week": current_week},
            "refreshAttendance": {"month": current_month, "week": current_week} # 月/週情報を含める
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
    
    このエンドポイントは、JavaScript APIから直接勤怠IDを指定して削除する場合に使用します。
    """
    try:
        attendance_obj = attendance.get_or_404(db=db, id=attendance_id)
        user_id = attendance_obj.user_id  # 削除前にユーザーIDを取得
        date_str = attendance_obj.date.isoformat()  # 削除前に日付を取得
        current_week = extract_week_from_request(request, cast(date, attendance_obj.date))
        
        attendance.remove(db=db, id=attendance_id)
        logger.debug(f"勤怠ID {attendance_id} の削除に成功しました")
        
        # 現在表示中の月情報を取得
        current_month = extract_month_from_request(request)
        
        # 勤怠UI更新用のトリガーデータ
        trigger_data = {
            "closeModal": f"attendance-modal-{user_id}-{date_str}",
            "refreshUserAttendance": {"user_id": user_id, "month": current_month, "week": current_week},
            "refreshAttendance": {"month": current_month, "week": current_week} # 月/週情報を含める
        }
        
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)}
        )
        
    except HTTPException:
        raise # HTTPExceptionはそのまま再送出
    except Exception as e:
        logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"勤怠データの削除中にエラーが発生しました: {str(e)}"
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_user_date(
    request: Request,
    user_id: str,
    date: date, # FastAPIが "YYYY-MM-DD" から date オブジェクトに変換
    db: Session = Depends(get_db),
) -> Response:
    """
    特定ユーザーの特定日の勤怠データを削除します。
    成功時には HX-Trigger ヘッダー付きで 204 No Content を返します。
    
    このエンドポイントは、モーダルUIから user_id と date を指定して削除する場合に使用します。
    """
    try:
        date_str = date.isoformat()
        current_week = extract_week_from_request(request, date)
        
        # 勤怠データを検索
        attendance_obj = attendance.get_by_user_and_date(db=db, user_id=user_id, date=date)
        if not attendance_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ユーザー '{user_id}' の日付 '{date_str}' の勤怠データが見つかりません"
            )
        
        # 勤怠データを削除
        attendance.remove(db=db, id=attendance_obj.id)
        logger.debug(f"ユーザー '{user_id}' の日付 '{date_str}' の勤怠削除に成功しました")
        
        # 現在表示中の月情報を取得
        current_month = extract_month_from_request(request)
        
        # モーダルを閉じて勤怠表示を更新するトリガー
        trigger_data = {
            "closeModal": f"attendance-modal-{user_id}-{date_str}",
            "refreshUserAttendance": {"user_id": user_id, "month": current_month, "week": current_week},
            "refreshAttendance": {"month": current_month, "week": current_week} # 月/週情報を含める
        }
        
        return Response(
            content="",
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": json.dumps(trigger_data)}
        )
        
    except HTTPException:
        raise # HTTPExceptionはそのまま再送出
    except Exception as e:
        logger.error(f"ユーザー/日付指定の勤怠削除エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"勤怠データの削除中にエラーが発生しました: {str(e)}"
        )
