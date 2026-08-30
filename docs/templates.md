# ディレクトリ構造
```
app/templates/
├── layout/                # ベースレイアウト (単数形に変更)
│   └── base.html          # ベースHTMLテンプレート
│
├── components/            # 全ての再利用可能なコンポーネント (partialsを統合)
│   ├── common/            # 共通UIコンポーネント
│   │   ├── head.html      # <head>タグの内容
│   │   ├── sidebar.html   # サイドバー
│   │   └── theme_switcher.html  # テーマ切替コンポーネント
│   │
│   ├── calendar/          # カレンダー関連コンポーネント
│   │   ├── summary_calendar.html  # 線形カレンダー表示
│   │   └── grid_calendar.html  # グリッドカレンダーコンポーネント
│   │
│   └── details/           # 詳細表示コンポーネント
│       ├── day_detail.html      # 日付詳細
│       ├── user_detail.html     # ユーザー詳細
│       └── attendance_table.html # 出席テーブル
│
└── pages/                 # 各ページテンプレート
    ├── index.html         # メインページ
    ├── attendance/        # 勤怠関連ページ
    ├── location/          # 勤務場所関連ページ
    ├── user/              # ユーザー関連ページ
    ├── user_type/         # ユーザータイプ関連ページ
    ├── csv/               # CSV関連ページ
    └── group/             # グループ関連ページ
```
