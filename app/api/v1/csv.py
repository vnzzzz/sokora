"""
CSVデータダウンロードAPI
=====================

CSVデータのダウンロードに関連するAPIエンドポイントを提供します。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.csv_utils import get_work_entries_csv
from app.core.config import logger

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
        # CSVデータを取得
        csv_content = get_work_entries_csv(db, month=month, encoding=encoding)
        
        # エンコーディングに応じたContent-Typeを設定
        content_type = "text/csv; charset=utf-8"
        if encoding.lower() == "sjis":
            content_type = "text/csv; charset=shift_jis"
        
        # ファイル名を設定
        filename = "work_entries.csv"
        if month:
            filename = f"work_entries_{month}.csv"
        
        # レスポンスを返す
        return StreamingResponse(
            iter([csv_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"CSVダウンロードエラー: {str(e)}", exc_info=True)
        # エラーが発生した場合も空のCSVを返す
        return StreamingResponse(
            iter([b"user_name,user_id,group_name,is_contractor,is_manager"]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=work_entries_error.csv"}
        ) 