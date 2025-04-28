"""
CSVデータダウンロードAPI
=====================

CSVデータのダウンロードに関連するAPIエンドポイントを提供します。
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.utils.csv_utils import get_work_entries_csv

# ルーター定義
router = APIRouter(prefix="/csv", tags=["Data"])

@router.get("/download")
def download_csv(
    month: Optional[str] = Query(None, description="フィルタリングする月（YYYY-MM形式）"),
    encoding: str = Query("utf-8", description="CSVエンコーディング（utf-8またはsjis）"),
    db: Session = Depends(get_db)
) -> Any:
    """
    勤怠データをCSV形式でダウンロードします

    Args:
        month: フィルタリングする月（YYYY-MM形式）
        encoding: CSVエンコーディング（utf-8またはsjis）
        db: データベースセッション

    Returns:
        StreamingResponse: CSVデータのストリームレスポンス
    """
    try:
        # 指定された月とエンコーディングで勤怠データをCSV形式で取得します。
        csv_content = get_work_entries_csv(db, month=month, encoding=encoding)

        # レスポンスヘッダーのContent-Typeを決定します。
        content_type = "text/csv; charset=utf-8"
        if encoding.lower() == "sjis":
            content_type = "text/csv; charset=shift_jis"

        # ダウンロード時のファイル名を決定します (月指定があればファイル名に含める)。
        filename = "work_entries.csv"
        if month:
            filename = f"work_entries_{month}.csv"

        # CSVデータをストリーミングレスポンスとして返します。
        return StreamingResponse(
            iter([csv_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"CSVダウンロード中にエラーが発生しました: {str(e)}", exc_info=True)
        # エラー発生時は、エラーを示すファイル名と空のヘッダー行を持つCSVを返します。
        error_csv_header = b"user_name,user_id,group_name,user_type" # エラー時のヘッダー
        return StreamingResponse(
            iter([error_csv_header]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=work_entries_error.csv"}
        ) 