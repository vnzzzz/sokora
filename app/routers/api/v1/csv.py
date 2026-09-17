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
from app.db.session import (
    DatabaseRuntimeUnavailableError,
    get_db,
    is_database_unavailable_error,
)
from app.utils.csv_utils import generate_work_entries_csv_rows

router = APIRouter(prefix="/csv", tags=["Data"])


def _prepare_csv_file(
    rows: Iterable[Sequence[str]],
    encoding: str = "utf-8",
) -> BinaryIO:
    """全CSV行をresponse開始前にdisk-backed temporary fileへ書き込む。

    Args:
        rows: CSVへ書き込む行のiterable。
        encoding: 出力encoding。`sjis`はShift_JIS、それ以外はUTF-8として扱う。

    Returns:
        先頭位置へrewind済みのbinary temporary file。

    Raises:
        Exception: 行生成・encoding・file書き込みに失敗した場合。作成済みfileはcloseして再送出する。
    """
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
    """生成済みtemporary fileをchunk単位でstreamする。

    Args:
        csv_file: 先頭位置へrewind済みのbinary file。

    Yields:
        最大64KiBのCSV byte chunk。

    Notes:
        stream完了時または中断時にfileを必ずcloseする。
    """
    try:
        while chunk := csv_file.read(64 * 1024):
            yield chunk
    finally:
        csv_file.close()


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
    """勤怠CSVを生成し、成功を確認してからdownload responseを返す。

    Args:
        month: 出力対象月。`YYYY-MM`形式。未指定時は全対象期間を出力する。
        encoding: `utf-8`または`sjis`。
        db: DB session。

    Returns:
        生成済みtemporary fileをstreamするCSV download response。

    Raises:
        HTTPException: month/encodingが不正、DBが利用不能、またはCSV生成に失敗した場合。
    """
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
        if is_database_unavailable_error(exc):
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
