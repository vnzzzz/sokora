# sokora

![image](docs/images/image1.png)

直感的なカレンダーインターフェースで勤務場所を可視化するアプリです。

## 機能

- インタラクティブなカレンダー UI
  - リモート/オフィス勤務の集計データを含む月間ビュー
- 日別詳細や個人スケジュールを表示
- CSV インポート/エクスポート

## 使い方

1. セットアップ

   `.env.sample`をコピーして`.env`を作成し、以下を実行:

   ```bash
   docker compose up --build
   ```

2. アクセス

   ブラウザで以下の URL にアクセス:

   ```bash
   http://localhost:[SERVICE_PORT]
   ```

3. シャットダウン

   ```bash
   docker compose down
   ```

## 技術スタック

パフォーマンスとシンプルさを重視しました。

- Docker (コンテナ化)
- Poetry (Python 依存関係管理)
- FastAPI (バックエンド API)
- HTMX & Alpine.js (ビルドステップ不要のフロントエンド)
- CSV ファイル (データベース不要のデータソース)
