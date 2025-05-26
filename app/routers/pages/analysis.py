"""
勤怠集計ページエンドポイント
================

勤怠集計に関連するルートハンドラー
"""

from typing import Any, Optional, Dict, List, Tuple
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.db.session import get_db

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/analysis", response_class=HTMLResponse)
def get_analysis_page(
    request: Request, 
    month: Optional[str] = None, 
    db: Session = Depends(get_db)
) -> Any:
    """勤怠集計ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされた勤怠集計HTML
    """
    try:
        # 勤怠集計データを取得
        analysis_data = attendance.get_attendance_analysis_data(db, month=month)
        
        # 月切り替え用の前月・次月を計算
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        # 現在の月を解析
        current_month = analysis_data["month"]
        year, month_num = map(int, current_month.split('-'))
        current_date = datetime(year, month_num, 1)
        
        # 前月・次月を計算
        prev_month_date = current_date - relativedelta(months=1)
        next_month_date = current_date + relativedelta(months=1)
        
        prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"
        next_month = f"{next_month_date.year}-{next_month_date.month:02d}"
        
        # グループと社員種別、勤怠種別の情報を取得してソート用の情報を準備
        from app.crud.group import group as group_crud
        from app.crud.user_type import user_type as user_type_crud
        from app.crud.location import location as location_crud
        
        groups = group_crud.get_multi(db)
        user_types = user_type_crud.get_multi(db)
        locations = location_crud.get_multi(db)
        
        # グループのソート情報を作成
        group_sort_info: Dict[str, Tuple[int, int]] = {}
        for group in groups:
            group_sort_info[str(group.name)] = (int(group.order or 999), int(group.id))
        
        # 社員種別のソート情報を作成
        user_type_sort_info: Dict[str, Tuple[int, int]] = {}
        for user_type in user_types:
            user_type_sort_info[str(user_type.name)] = (int(user_type.order or 999), int(user_type.id))
        
        # 勤怠種別を分類→順序でソート
        sorted_locations = sorted(locations, key=lambda x: (str(x.category or ""), int(x.order or 999), int(x.id)))
        
        # analysis_dataのlocationsを順序付きに置き換え
        analysis_data["locations"] = sorted_locations
        
        # グループ別にユーザーを整理
        grouped_users: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        group_user_types: Dict[str, List[str]] = {}  # 各グループの社員種別リスト（順序付き）
        
        for user_id, user_info in analysis_data["users"].items():
            group_name = user_info["group_name"] or "未分類"
            if group_name not in grouped_users:
                grouped_users[group_name] = []
                group_user_types[group_name] = []
            grouped_users[group_name].append((user_id, user_info))
        
        # 各グループ内でユーザーを社員種別順にソート
        for group_name in grouped_users:
            grouped_users[group_name].sort(
                key=lambda x: user_type_sort_info.get(str(x[1]["user_type_name"] or ""), (999, 999))
            )
            
            # このグループの社員種別リストを作成（順序付き、重複なし）
            user_types_in_group = []
            seen_types = set()
            for user_id, user_info in grouped_users[group_name]:
                user_type_name = user_info["user_type_name"] or "未分類"
                if user_type_name not in seen_types:
                    user_types_in_group.append(user_type_name)
                    seen_types.add(user_type_name)
            group_user_types[group_name] = user_types_in_group
        
        # グループ名をorder順にソート
        sorted_group_names = sorted(
            grouped_users.keys(),
            key=lambda x: group_sort_info.get(str(x), (999, 999))
        )
        
        context = {
            "request": request,
            "analysis_data": analysis_data,
            "current_month": analysis_data["month"],
            "prev_month": prev_month,
            "next_month": next_month,
            "grouped_users": grouped_users,
            "sorted_group_names": sorted_group_names,
            "group_user_types": group_user_types
        }
        
        return templates.TemplateResponse("pages/analysis.html", context)
        
    except Exception as e:
        logger.error(f"勤怠集計ページ表示中にエラーが発生しました: {str(e)}", exc_info=True)
        # エラー時は空のデータで表示
        context = {
            "request": request,
            "analysis_data": {
                "month": month or "",
                "month_name": "エラー",
                "users": {},
                "locations": [],
                "summary": {"total_users": 0, "total_attendance_days": 0}
            },
            "current_month": month or "",
            "prev_month": "",
            "next_month": "",
            "grouped_users": {},
            "sorted_group_names": []
        }
        return templates.TemplateResponse("pages/analysis.html", context) 