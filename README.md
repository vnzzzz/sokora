# sokora

![image](docs/images/image1.png)

直感的なカレンダーインターフェースで勤務場所を可視化するアプリです。

## 機能

- インタラクティブなカレンダー UI
  - リモート/オフィス勤務の集計データを含む月間ビュー
- 日別詳細や個人スケジュールを表示

## 使い方

1. セットアップ

   `.env.sample`をコピーして`.env`を作成し、以下の手順でイメージをビルドしてコンテナを実行します:

   ```bash
   # イメージをビルド
   docker build -t sokora:latest .

   # コンテナを起動
   docker compose up
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

## 開発環境

### VSCode DevContainer

このプロジェクトは VSCode DevContainer に対応しており、開発環境を簡単に構築できます。

1. VSCode と Docker をインストール
2. VSCode の拡張機能
   [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) をイン
   ストール
3. プロジェクトを VSCode で開き、`Remote-Containers: Reopen in Container`を実行

詳細は`.devcontainer/README.md`を参照してください。

## 技術スタック

パフォーマンスとシンプルさを重視しました。

- Docker (コンテナ化)
- Poetry (Python 依存関係管理)
- FastAPI (バックエンド API)
- HTMX & Alpine.js (ビルドステップ不要のフロントエンド)
- SQLite (軽量データベース)
