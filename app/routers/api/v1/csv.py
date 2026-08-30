"""
CSVデータダウンロードAPI
=====================

CSVデータのダウンロードに関連するAPIエンドポイントを提供します。
"""
import csv
import io
from typing import Optional, Generator, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.utils.csv_utils import generate_work_entries_csv_rows

# ルーター定義
router = APIRouter(prefix="/csv", tags=["Data"])

def _iter_csv(row_generator: Generator[List[str], None, None], encoding: str = "utf-8") -> Generator[bytes, None, None]:
    """CSV行ジェネレータを受け取り、エンコードされたバイト列をyieldするジェネレータ"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    try:
        for row in row_generator:
            writer.writerow(row)
            buffer.seek(0)
            data = buffer.read()
            buffer.seek(0)
            buffer.truncate()
            # エンコードしてyield
            if encoding.lower() == "sjis":
                yield data.encode("shift_jis", errors="replace")
            else:
                yield data.encode("utf-8")
    except Exception as e:
         logger.error(f"CSVストリーミング中にエラー: {e}", exc_info=True)
         # エラー発生時にも何らかのバイト列を返す (例: エラーメッセージ)
         error_msg = f"Error during CSV generation: {e}\n"
         if encoding.lower() == "sjis":
             yield error_msg.encode("shift_jis", errors="replace")
         else:
             yield error_msg.encode("utf-8")
    finally:
        buffer.close()

@router.get("/download")
def download_csv(
    month: Optional[str] = Query(None, description="フィルタリングする月（YYYY-MM形式）"),
    encoding: str = Query("utf-8", description="CSVエンコーディング（utf-8またはsjis）"),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    勤怠データをCSV形式でストリーミングダウンロードします
    """
    logger.info(f"CSVダウンロードリクエスト: month={month}, encoding={encoding}")
    
    # エンコーディング検証
    valid_encodings = ["utf-8", "sjis"]
    normalized_encoding = encoding.lower()
    if normalized_encoding not in valid_encodings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効なエンコーディングです: {encoding}. 利用可能なエンコーディング: {', '.join(valid_encodings)}"
        )
        
    # 月フォーマット検証 (YYYY-MM)
    if month:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail="月の形式が無効です。YYYY-MM形式で指定してください。"
             )

    try:
        # CSV行ジェネレータを取得
        row_generator = generate_work_entries_csv_rows(db, month=month)

        # コンテンツタイプとファイル名を設定
        media_type = "text/csv"
             
        filename = "work_entries.csv"
        if month:
            filename = f"work_entries_{month}.csv"

        response_headers = {
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
        }
        # SJIS指定の場合はContent-Typeヘッダーを上書き
        if normalized_encoding == "sjis":
            response_headers["Content-Type"] = "text/csv; charset=shift_jis"

        # ストリーミングレスポンスを返す
        return StreamingResponse(
            _iter_csv(row_generator, normalized_encoding),
            media_type=media_type,
            headers=response_headers
        )

    except Exception as e:
        # ジェネレータ生成など、ストリーム開始前のエラー
        logger.error(f"CSVダウンロード準備中にエラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSVファイルの生成中にエラーが発生しました。"
        ) 