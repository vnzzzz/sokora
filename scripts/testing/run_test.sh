#!/bin/bash

# テスト実行スクリプト
# 使用方法: プロジェクトルートから ./scripts/testing/run_test.sh を実行

echo "Running tests..."
# プロジェクトルート (/app) から pytest を実行
export PYTHONPATH="/app:${PYTHONPATH}"  # PYTHONPATH に /app を追加
poetry run pytest tests/ 