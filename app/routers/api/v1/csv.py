"""CSVデータダウンロードAPI。"""

import csv
import io
import tempfile
from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from typing import BinaryIO, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import DatabaseRuntimeUnavailableError, get_db
from app.utils.csv_utils import generate_work_entries_csv_rows

router = APIRouter(prefix="/csv", tags=["Data"])


def _prepare_csv_file(
    rows: Iterable[Sequence[str]],
    encoding: str = "utf-8",
) -> BinaryIO:
    """全CSV行をresponse開始前にdisk-backed temporary fileへ書き込む。"""
    csv_file = tempfile.TemporaryFile(mode="w+b")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    try:
        for row in rows:
            writer.writerow(row)
            data = buffer.getvalue()
            if encoding.lower() == "sjis":
                csv_file.write(data.encode("shift_jis", errors="replace"))
            else:
                csv_file.write(data.encode("utf-8"))
            buffer.seek(0)
            buffer.truncate(0)
        csv_file.seek(0)
        return csv_file
    except Exception:
        csv_file.close()
        raise
    finally:
        buffer.close()


def _stream_prepared_csv(csv_file: BinaryIO) -> Iterator[bytes]:
    """生成済みtemporary fileをchunk単位で返し、stream終了時に必ずcloseする。"""
    try:
        while chunk := csv_file.read(64 * 1024):
            yield chunk
    finally:
        csv_file.close()


def _is_database_unavailable_error(exc: Exception) -> bool:
    """verified disconnect / connection acquisition failureだけをavailability errorとする。"""
    if isinstance(exc, (DatabaseRuntimeUnavailableError, SQLAlchemyTimeoutError)):
        return True
    return isinstance(exc, DBAPIError) and (
        exc.connection_invalidated or exc.statement is None
    )


@router.get("/download")
def download_csv(
    month: Optional[str] = Query(
        None, description="フィルタリングする月（YYYY-MM形式）"
    ),
    encoding: str = Query(
        "utf-8", description="CSVエンコーディング（utf-8またはsjis）"
    ),
    db: Session = Depends(get_db),
) -> StreamingResponse:
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
        csv_file = _prepare_csv_file(
            generate_work_entries_csv_rows(db, month=month),
            normalized_encoding,
        )
    except (DatabaseRuntimeUnavailableError, DBAPIError, SQLAlchemyTimeoutError) as exc:
        if _is_database_unavailable_error(exc):
            logger.error("CSV生成時にDBを利用できません: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="データベースが一時的に利用できないため、CSVを生成できません。",
            ) from exc
        logger.error(
            "CSV生成中にDB statement errorが発生しました: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSVファイルの生成中にエラーが発生しました。",
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

    return StreamingResponse(
        _stream_prepared_csv(csv_file),
        media_type="text/csv",
        headers=response_headers,
    )
