"""
CSV関連エンドポイント
----------------

CSVデータのインポートとエクスポートに関連するルートハンドラー
"""

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import csv
from typing import Optional
import tempfile
import shutil

from ...services import csv_store
from ...utils.date_utils import get_today_formatted
from ...utils.common import generate_location_badges, has_data_for_day
from ...utils.file_utils import get_csv_file_path, read_csv_file

router = APIRouter(prefix="/api/csv", tags=["CSVデータ"])
templates = Jinja2Templates(directory="src/templates")


@router.post("/import")
async def import_csv(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    """Import a CSV file

    Args:
        request: FastAPI request object
        file: Uploaded CSV file

    Returns:
        HTMLResponse: HTML response with import results
    """
    try:
        contents = await file.read()
        # Try to decode with different encodings
        try:
            # Try UTF-8 with BOM first
            content_str = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                # Try UTF-8 without BOM
                content_str = contents.decode("utf-8")
            except UnicodeDecodeError:
                # Fallback to SHIFT-JIS (common on Windows in Japan)
                content_str = contents.decode("shift-jis")

        csv_store.import_csv_data(content_str)

        # Get today's data and create context
        today_str = get_today_formatted()
        day_data = csv_store.get_day_data(today_str)

        # Get types of work locations
        location_types = csv_store.get_location_types()

        # Generate badge information for work locations
        locations = generate_location_badges(location_types)

        # Check if data exists
        has_data = has_data_for_day(day_data)

        context = {
            "request": request,
            "day": today_str,
            "data": day_data,
            "locations": locations,
            "has_data": has_data,
            "success_message": "CSV data imported successfully.",
        }

        return templates.TemplateResponse("partials/day_detail.html", context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV import error: {str(e)}")


@router.get("/export")
def export_csv(
    encoding: Optional[str] = Query("utf-8", description="CSV file encoding")
) -> FileResponse:
    """Export attendance data as CSV

    Args:
        encoding: Encoding to use for the CSV file (utf-8 or shift-jis)

    Returns:
        FileResponse: CSV file download response
    """
    csv_path = get_csv_file_path()

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file not found")

    # Check valid encoding
    if encoding not in ["utf-8", "shift-jis"]:
        encoding = "utf-8"  # Default to UTF-8

    filename = "work_entries.csv"

    # If UTF-8 is requested, return file as is
    if encoding == "utf-8":
        return FileResponse(
            path=csv_path,
            filename=filename,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8-sig",
            },
        )

    # For Shift-JIS encoding, convert to temp file
    else:  # encoding == "shift-jis"
        # Read CSV content
        headers, rows = read_csv_file()

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
            temp_path = temp_file.name

            # Write CSV with Shift-JIS encoding
            with open(temp_path, "w", encoding="shift_jis", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

        # Return the temp file
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=shift-jis",
            },
            background=shutil.rmtree(
                temp_path, ignore_errors=True
            ),  # Remove temp file after response
        )
