#!/bin/bash

# データシーダー実行スクリプト
# 使用方法: プロジェクトルートから ./scripts/seeding/run_seeder.sh [ユーザー数] [過去日数] [未来日数] を実行

USER_COUNT=${1:-50}  # デフォルト: 50
DAYS_BACK=${2:-60}   # デフォルト: 60
DAYS_FORWARD=${3:-60}  # デフォルト: 60

# プロジェクトルートから実行する必要があるため、カレントディレクトリをチェック (任意)
# if [ "$(basename "$(pwd)")" != "sokora" ]; then
#   echo "Error: このスクリプトはプロジェクトルートディレクトリから実行してください。" >&2
#   exit 1
# fi

# Pythonコードを実行してシーダーを起動
# インポートパスを修正: app.data_seeder -> scripts.seeding
python3 -c "
import sys
import os
# プロジェクトルートをPythonパスに追加 (確実性のため)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.seeding.data_seeder import run_seeder

print('データシーダー実行中...')
print(f'パラメータ: ユーザー数=${USER_COUNT}, 過去日数=${DAYS_BACK}, 未来日数=${DAYS_FORWARD}')

result = run_seeder(
    user_count=${USER_COUNT}, 
    days_back=${DAYS_BACK}, 
    days_forward=${DAYS_FORWARD}
)

print('完了しました！')
print(f'追加されたデータ:')
print(f'- ユーザー: {result["users"]}')
print(f'- 勤怠記録: {result["attendances"]}')
" 