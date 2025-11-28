# ディレクトリ構造

UI 全体の要件や画面ごとの振る舞いは `docs/ui/requirements.md` を参照し、ここではテンプレート配置のみを簡潔に示します。

## 静的ファイル (`app/static`)

```
app/static/
├── css/                   # CSSファイル
│   ├── main.css           # アプリケーション全体の基本スタイル
│   └── calendar.css       # カレンダー表示用の追加スタイル
│
├── js/                    # JavaScriptファイル
│   ├── alpine.min.js      # Alpine.js ライブラリ（最小化版）
│   ├── htmx.min.js        # HTMX ライブラリ（最小化版）
│   ├── apiClient.js       # FastAPIバックエンドとの通信用クライアント
│   ├── calendar.js        # カレンダー関連のインタラクション（日付選択、月移動等）
│   ├── attendance.js      # 勤怠登録・編集カレンダーのインタラクション
│   ├── modal-handlers.js  # 共通モーダルのフォーム送信処理
│   ├── main.js            # サイドバー開閉、テーマ切り替え等の共通UI処理
│   └── circle-favicon.js  # ファビコンに円を描画する処理（開発用）
│
└── favicon.ico            # アプリケーションのファビコン
```

```
app/templates/
├── layout/                # ベースレイアウト
│   └── base.html          # ベースHTMLテンプレート（ヘッダー、サイドバー、フッター等を含む）
│
├── components/            # 再利用可能なコンポーネント
│   ├── common/            # アプリケーション全体で共通のUI部品
│   │   ├── head.html      # HTMLの<head>セクション（メタタグ、CSSリンク等）
│   │   ├── sidebar.html   # ナビゲーション用サイドバー
│   │   ├── theme_switcher.html  # ライト/ダークテーマ切り替えボタン
│   │   ├── modal.html     # 追加/編集/削除確認用の共通モーダルマクロ
│   │   └── month_switcher.html # カレンダー表示用の月移動ボタン
│   │
│   └── calendar/          # カレンダー表示に関連するコンポーネント
│       └── summary_calendar.html  # 月表示の集計カレンダー（線形表示）
│
└── pages/                 # 各機能ページのテンプレート
    ├── main/              # メインの勤怠表示関連ページ
    │   ├── index.html     # メインカレンダー表示ページ（summary_calendarを読み込む）
    │   └── day_detail.html  # 特定日の勤怠詳細表示用（HTMX部分テンプレート）
    ├── attendance/        # 勤怠編集・登録関連ページ
    │   ├── index.html     # 勤怠データ一覧表示ページ（現在未使用の可能性あり）
    │   └── attendance_calendar.html # 勤怠編集用カレンダー表示（HTMX部分テンプレート）
    ├── location/          # 勤怠種別管理ページ
    │   └── index.html     # 勤怠種別一覧、追加、編集、削除機能
    ├── user/              # 社員管理ページ
    │   └── index.html     # 社員一覧、追加、編集、削除機能
    ├── user_type/         # 社員種別管理ページ
    │   └── index.html     # 社員種別一覧、追加、編集、削除機能
    ├── csv/               # CSVインポート/エクスポートページ
    │   └── index.html     # 勤怠データCSVのアップロード・ダウンロード機能
    └── group/             # グループ管理ページ
        └── index.html     # グループ一覧、追加、編集、削除機能
```
