"""
CSV-Related Endpoints
----------------

Route handlers related to CSV data import and export
"""

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os

from .. import csv_store
from ..utils.date_utils import get_today_formatted
from ..utils.common import generate_location_badges, has_data_for_day
from ..utils.file_utils import get_csv_file_path

router = APIRouter(prefix="/api/csv", tags=["CSV Data"])
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
        csv_store.import_csv_data(contents.decode("utf-8"))

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
def export_csv() -> FileResponse:
    """Export attendance data as CSV

    Returns:
        FileResponse: CSV file download response
    """
    csv_path = get_csv_file_path()

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file not found")

    filename = "work_entries.csv"
    return FileResponse(
        path=csv_path,
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
