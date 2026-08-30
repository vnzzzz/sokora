#!/bin/bash

# データシーダー実行スクリプト
# 使用方法: ./run_seeder.sh [ユーザー数] [過去日数] [未来日数]

USER_COUNT=${1:-50}  # デフォルト: 50
DAYS_BACK=${2:-60}   # デフォルト: 60
DAYS_FORWARD=${3:-60}  # デフォルト: 60

# Pythonコードを実行してシーダーを起動
python3 -c "
from app.data_seeder.data_seeder import run_seeder

print('データシーダー実行中...')
print(f'パラメータ: ユーザー数=${USER_COUNT}, 過去日数=${DAYS_BACK}, 未来日数=${DAYS_FORWARD}')

result = run_seeder(
    user_count=${USER_COUNT}, 
    days_back=${DAYS_BACK}, 
    days_forward=${DAYS_FORWARD}
)

print('完了しました！')
print(f'追加されたデータ:')
print(f'- ユーザー: {result[\"users\"]}')
print(f'- 勤怠記録: {result[\"attendances\"]}')
" 