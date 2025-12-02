#!/bin/bash

# テスト実行スクリプト（クリーンアップ・検証付き）
# 使用方法: プロジェクトルートから ./scripts/testing/run_test.sh を実行

# PYTHONPATH に /app を追加 (一度だけ実行)
export PYTHONPATH="/app:${PYTHONPATH}"
# 認証ガードを明示的に無効化して、UI/API テストを環境差分なく実行する
export SOKORA_AUTH_ENABLED="false"

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

# サーバ起動ヘルパー
SERVER_PID=""
SERVER_MANAGED=0

function cleanup_server() {
  if [ "$SERVER_MANAGED" -eq 1 ] && [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup_server EXIT

function is_server_running() {
  python3 - <<'PY'
import sys, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8000", timeout=1) as resp:
        sys.exit(0 if resp.status < 500 else 1)
except Exception:
    sys.exit(1)
PY
}

if ! is_server_running; then
  echo "🚀 E2E用にアプリサーバーを起動します (http://127.0.0.1:8000)..."
  poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning > /tmp/e2e_server.log 2>&1 &
  SERVER_PID=$!
  SERVER_MANAGED=1
  # 起動待ち
  for i in {1..30}; do
    if is_server_running; then
      echo "✅ アプリサーバーが起動しました (PID: $SERVER_PID)"
      break
    fi
    sleep 1
  done
  if ! is_server_running; then
    echo "❌ アプリサーバーの起動に失敗しました。ログ: /tmp/e2e_server.log"
    exit 1
  fi
else
  echo "ℹ️  既存のアプリサーバーが検出されました。再利用します。"
fi

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
