#!/bin/bash

# テスト実行スクリプト（クリーンアップ・検証付き）
# 使用方法: プロジェクトルートから ./scripts/testing/run_test.sh を実行

# PYTHONPATH に /app を追加 (一度だけ実行)
export PYTHONPATH="/app:${PYTHONPATH}"

echo "=========================================="
echo "🧹 テスト実行前のクリーンアップ・検証"
echo "=========================================="

# テスト実行前のDB状態確認
echo "📊 テスト実行前のDB状態を確認しています..."
python3 app/tests/utils/db_checker.py

# テスト関連データが残っている場合はクリーンアップ
echo ""
echo "🧽 残存テストデータのクリーンアップを実行しています..."
python3 app/tests/utils/data_cleanup.py

# クリーンアップ後の状態確認
echo ""
echo "✅ クリーンアップ後のDB状態を確認しています..."
python3 app/tests/utils/db_checker.py

echo ""
echo "=========================================="
echo "🧪 API・ユニットテスト実行"
echo "=========================================="

# API/ユニットテストを実行 (e2e を除く)
poetry run pytest -vv app/tests/routers/ app/tests/crud/ app/tests/services/ app/tests/utils/

# APIテストが失敗したらスクリプトを終了
if [ $? -ne 0 ]; then
    echo "❌ API/Unit tests failed. Exiting."
    exit 1
fi

echo ""
echo "=========================================="
echo "🎭 E2Eテスト実行"
echo "=========================================="

# E2Eテストを実行
poetry run pytest -vv app/tests/e2e/

# E2Eテストが失敗したらスクリプトを終了
if [ $? -ne 0 ]; then
    echo "❌ E2E tests failed. Exiting."
    exit 1
fi

echo ""
echo "=========================================="
echo "🔍 テスト実行後の検証・クリーンアップ"
echo "=========================================="

# テスト実行後のDB状態確認
echo "📊 テスト実行後のDB状態を確認しています..."
TEST_DATA_COUNT=$(python3 -c "
import sys
sys.path.insert(0, '/app')
from app.tests.utils.db_checker import has_test_data, check_database
count = check_database()
if count == 0:
    print('0')
else:
    print(str(count))
" 2>/dev/null | tail -1)

echo ""
if [ "$TEST_DATA_COUNT" != "0" ] && [ -n "$TEST_DATA_COUNT" ]; then
    echo "⚠️  警告: テスト実行後にテスト関連データが残存しています（${TEST_DATA_COUNT}件）"
    echo "🧽 残存データのクリーンアップを実行しています..."
    python3 app/tests/utils/data_cleanup.py
    
    # 最終確認
    echo ""
    echo "✅ 最終確認のDB状態:"
    python3 app/tests/utils/db_checker.py
else
    echo "✅ テスト関連データの残存なし。クリーンアップが正常に動作しています。"
fi

echo ""
echo "=========================================="
echo "🎉 すべてのテストが正常に完了しました！"
echo "=========================================="
exit 0 