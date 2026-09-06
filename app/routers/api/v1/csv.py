"""CSVデータダウンロードAPI。"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import DatabaseRuntimeUnavailableError, get_db
from app.utils.csv_utils import generate_work_entries_csv_rows

router = APIRouter(prefix="/csv", tags=["Data"])


def _encode_csv(rows: Iterable[Sequence[str]], encoding: str = "utf-8") -> bytes:
    """全CSV行をresponse開始前にencodeし、生成失敗をcallerへ伝播する。"""
    with io.StringIO(newline="") as buffer:
        writer = csv.writer(buffer)
        writer.writerows(rows)
        csv_text = buffer.getvalue()

    if encoding.lower() == "sjis":
        return csv_text.encode("shift_jis", errors="replace")
    return csv_text.encode("utf-8")


@router.get("/download")
def download_csv(
    month: Optional[str] = Query(
        None, description="フィルタリングする月（YYYY-MM形式）"
    ),
    encoding: str = Query(
        "utf-8", description="CSVエンコーディング（utf-8またはsjis）"
    ),
    db: Session = Depends(get_db),
) -> Response:
    """勤怠CSVを生成し、成功を確認してからdownload responseを返す。"""
    logger.info("CSVダウンロードリクエスト: month=%s, encoding=%s", month, encoding)

    valid_encodings = ["utf-8", "sjis"]
    normalized_encoding = encoding.lower()
    if normalized_encoding not in valid_encodings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効なエンコーディングです: {encoding}. 利用可能なエンコーディング: {', '.join(valid_encodings)}",
        )

    if month:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="月の形式が無効です。YYYY-MM形式で指定してください。",
            )

    try:
        csv_content = _encode_csv(
            generate_work_entries_csv_rows(db, month=month),
            normalized_encoding,
        )
    except (
        DatabaseRuntimeUnavailableError,
        OperationalError,
        InterfaceError,
        SQLAlchemyTimeoutError,
    ) as exc:
        logger.error("CSV生成時にDBを利用できません: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="データベースが一時的に利用できないため、CSVを生成できません。",
        ) from exc
    except Exception as exc:
        logger.error("CSV生成中に内部エラーが発生しました: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSVファイルの生成中にエラーが発生しました。",
        ) from exc

    filename = f"work_entries_{month}.csv" if month else "work_entries.csv"
    response_headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if normalized_encoding == "sjis":
        response_headers["Content-Type"] = "text/csv; charset=shift_jis"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers=response_headers,
    )
