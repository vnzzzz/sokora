#!/bin/bash

# テスト実行スクリプト
# 使用方法: プロジェクトルートから ./scripts/testing/run_test.sh を実行

# PYTHONPATH に /app を追加 (一度だけ実行)
export PYTHONPATH="/app:${PYTHONPATH}"

echo "Running API and unit tests..."
# API/ユニットテストを実行 (e2e を除く)
poetry run pytest app/tests/routers/ app/tests/crud/ app/tests/services/ app/tests/utils/

# APIテストが失敗したらスクリプトを終了
if [ $? -ne 0 ]; then
    echo "API/Unit tests failed. Exiting."
    exit 1
fi

echo "\nRunning E2E tests..."
# E2Eテストを実行
poetry run pytest app/tests/e2e/

# E2Eテストが失敗したらスクリプトを終了
if [ $? -ne 0 ]; then
    echo "E2E tests failed. Exiting."
    exit 1
fi

echo "\nAll tests passed successfully!"
exit 0 