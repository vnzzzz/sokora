# テンプレート配置ガイド

UI 全体の要件や画面ごとの振る舞いは `docs/ui/requirements.md` を参照し、ここではテンプレート・静的ファイルの配置と責務のみを簡潔に示します。

## 静的ファイル (`app/static`)

```text
app/static/
├── css/
│   └── calendar.css                # カレンダー表示固有のスタイル
├── js/
│   ├── analysis.js                 # 分析画面のインタラクション
│   ├── attendance-interactions.js  # 勤怠modal、月/週state、calendar再取得
│   ├── calendar.js                 # トップカレンダーの日付選択・日別詳細
│   ├── ui-events.js                # HTMX共通UI event（modal、message、page refresh）
│   ├── main.js                     # theme、sidebar、HTMX共通設定
│   ├── htmx-json-enc.js            # HTMX JSON encoding extension
│   └── circle-favicon.js           # favicon生成
└── favicon.ico
```

`attendance-interactions.js` と `ui-events.js` は #66 で分離した責務境界です。新しい共通HTMX event処理をpage固有scriptや`base.html`へ重複実装しません。`calendar.js` はトップカレンダーの表示操作に限定し、勤怠登録・編集後の再取得は `attendance-interactions.js` が担当します。

Alpine.js / HTMX などのvendor bundleはdev asset準備時に `/assets/js` へ配置されるため、アプリケーション固有JSの配置先として `app/static/js` にvendor copyを追加しません。

## テンプレート (`app/templates`)

```text
app/templates/
├── layout/
│   └── base.html                    # 共通layoutと共通script読込
├── components/
│   ├── common/                      # head/sidebar/theme等の共通partial
│   ├── macros/
│   │   ├── attendance.html          # 勤怠modal
│   │   ├── forms.html               # form error表示
│   │   ├── master_page.html         # master一覧header/empty state
│   │   ├── modal.html               # form/delete dialog shell
│   │   ├── navigation.html          # 月/週switcher
│   │   └── ui.html                  # 既存template向けcompatibility facade
│   ├── partials/                    # modal/register等のHTMX partial
│   └── {analysis,group,holiday,location,top,user,user_type}/
│                                      # 各画面固有の表示component
└── pages/
    ├── top.html
    ├── attendance.html
    ├── register.html
    ├── analysis.html
    ├── csv.html
    ├── group.html
    ├── holiday.html
    ├── location.html
    ├── user.html
    ├── user_type.html
    └── auth/                         # 認証画面
```

新規templateでは、必要な責務のmacro (`forms.html` / `modal.html` / `navigation.html` / `attendance.html` / `master_page.html`) を直接importします。`ui.html` は未移行templateの互換性維持用であり、新しい共通macroを集約する場所にはしません。
