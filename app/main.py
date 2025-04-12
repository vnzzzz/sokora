from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import datetime

from . import csv_store

app = FastAPI()

# 静的ファイルを /static で配信
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def root_page(request: Request):
    # デフォルトで今日のデータを取得
    today = datetime.date.today()
    today_str = f"{today.year}-{today.month:02d}-{today.day:02d}"
    day_data = csv_store.get_day_data(today_str)

    context = {"request": request, "default_day": today_str, "default_data": day_data}
    return templates.TemplateResponse("base.html", context)


@app.get("/api/calendar", response_class=HTMLResponse)
def get_calendar(request: Request, month: str = None):
    if month is None:
        # デフォルトで今月を表示
        today = datetime.date.today()
        month = f"{today.year}-{today.month:02d}"

    calendar_data = csv_store.get_calendar_data(month)
    context = {
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
    }
    return templates.TemplateResponse("partials/calendar.html", context)


@app.get("/api/day/{day}", response_class=HTMLResponse)
def get_day_detail(request: Request, day: str):
    detail = csv_store.get_day_data(day)
    context = {"request": request, "day": day, "data": detail}
    return templates.TemplateResponse("partials/day_detail.html", context)


@app.get("/api/user/{username}", response_class=HTMLResponse)
def get_user_detail(request: Request, username: str):
    user_entries = csv_store.get_user_data(username)
    context = {"request": request, "username": username, "entries": user_entries}
    return templates.TemplateResponse("partials/user_detail.html", context)


@app.post("/api/csv/import")
def import_csv(file: UploadFile = File(...)):
    contents = file.file.read().decode("utf-8")
    csv_store.import_csv_data(contents)
    return {"status": "ok", "message": "CSV imported successfully"}


@app.get("/api/csv/export")
def export_csv():
    csv_path = Path("work_entries.csv")
    return FileResponse(csv_path, media_type="text/csv", filename="work_entries.csv")
