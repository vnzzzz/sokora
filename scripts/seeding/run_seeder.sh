#!/bin/bash

# データシーダー実行スクリプト
# 使用方法: プロジェクトルートから ./scripts/seeding/run_seeder.sh [過去日数] [未来日数] を実行

DAYS_BACK=${1:-60}   # デフォルト: 60
DAYS_FORWARD=${2:-60}  # デフォルト: 60

# uv環境で data_seeder.py をモジュールとして実行
uv run python -m scripts.seeding.data_seeder --days-back "${DAYS_BACK}" --days-forward "${DAYS_FORWARD}"
