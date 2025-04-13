"""
CSV関連のエンドポイント
----------------

CSVデータのインポートとエクスポートに関連するルートハンドラー
"""

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os

from .. import csv_store
from ..utils.date_utils import get_today_formatted
from ..utils.common import generate_location_badges, has_data_for_day
from ..utils.file_utils import get_csv_file_path

router = APIRouter(prefix="/api/csv", tags=["CSVデータ"])
templates = Jinja2Templates(directory="src/templates")


@router.post("/import")
async def import_csv(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    """CSVファイルをインポートする

    Args:
        request: FastAPIリクエストオブジェクト
        file: アップロードされたCSVファイル

    Returns:
        HTMLResponse: インポート結果のHTMLレスポンス
    """
    try:
        contents = await file.read()
        csv_store.import_csv_data(contents.decode("utf-8"))

        # 今日のデータを取得してコンテキストを作成
        today_str = get_today_formatted()
        day_data = csv_store.get_day_data(today_str)

        # 勤務場所の種類を取得
        location_types = csv_store.get_location_types()

        # 勤務場所のバッジ情報を生成
        locations = generate_location_badges(location_types)

        # データがあるかどうかをチェック
        has_data = has_data_for_day(day_data)

        context = {
            "request": request,
            "day": today_str,
            "data": day_data,
            "locations": locations,
            "has_data": has_data,
            "success_message": "CSVデータが正常にインポートされました。",
        }

        return templates.TemplateResponse("partials/day_detail.html", context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSVインポートエラー: {str(e)}")


@router.get("/export")
def export_csv() -> FileResponse:
    """勤務データをCSV形式でエクスポートする

    Returns:
        FileResponse: CSVファイルのダウンロードレスポンス
    """
    csv_path = get_csv_file_path()

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSVファイルが見つかりません")

    filename = "work_entries.csv"
    return FileResponse(
        path=csv_path,
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
