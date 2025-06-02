#!/usr/bin/env python3
"""
ビルド時祝日データ取得スクリプト
============================

コンテナビルド時にHolidays JP APIから祝日データを取得し、
ローカルファイルにキャッシュする。
"""

import json
import os
import sys
import datetime
from typing import Dict
from pathlib import Path
import httpx

# データディレクトリの設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_FILE = DATA_DIR / "holidays_cache.json"

# Holidays JP API のベースURL
HOLIDAYS_API_BASE = "https://holidays-jp.github.io/api/v1"


def fetch_holidays_from_api(year: int) -> Dict[str, str]:
    """指定年の祝日データをAPIから取得する"""
    try:
        url = f"{HOLIDAYS_API_BASE}/{year}/date.json"
        print(f"祝日データを取得中: {url}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            
            holidays = response.json()
            print(f"{year}年の祝日データを取得しました: {len(holidays)}件")
            return holidays
            
    except Exception as e:
        print(f"ERROR: {year}年の祝日データ取得に失敗しました: {e}")
        return {}


def build_holiday_cache() -> None:
    """祝日キャッシュを構築する"""
    current_year = datetime.datetime.now().year
    
    # 過去2年、現在年、未来3年のデータを取得（計6年分）
    years_to_fetch = range(current_year - 2, current_year + 4)
    
    all_holidays = {}
    
    print(f"祝日データを取得中: {min(years_to_fetch)}-{max(years_to_fetch)}年")
    
    for year in years_to_fetch:
        holidays = fetch_holidays_from_api(year)
        if holidays:
            all_holidays.update(holidays)
        else:
            print(f"WARNING: {year}年の祝日データが取得できませんでした")
    
    if not all_holidays:
        print("ERROR: 祝日データが一つも取得できませんでした")
        sys.exit(1)
    
    # ディレクトリが存在しない場合は作成
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # キャッシュデータの保存
    cache_data = {
        'holidays': all_holidays,
        'last_updated_year': current_year,
        'updated_at': datetime.datetime.now().isoformat(),
        'build_time': True  # ビルド時に作成されたことを示すフラグ
    }
    
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"祝日キャッシュを保存しました: {len(all_holidays)}件 -> {CACHE_FILE}")
        
    except Exception as e:
        print(f"ERROR: 祝日キャッシュの保存に失敗しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=== 祝日データビルドスクリプト ===")
    build_holiday_cache()
    print("=== 祝日データビルド完了 ===") 