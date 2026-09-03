# Template and static asset layout

UIの利用者向けbehaviorは [UI requirements](./requirements.md) をSSoTとし、この文書ではJinja templateとapplication static assetの**配置と責務**だけを示す。個別routeやHTMX response contractは重複記載しない。

## Static files (`app/static`)

```text
app/static/
├── css/
│   └── calendar.css
├── js/
│   ├── analysis.js
│   ├── attendance-interactions.js
│   ├── calendar.js
│   ├── circle-favicon.js
│   ├── htmx-json-enc.js
│   ├── main.js
│   └── ui-events.js
└── favicon.ico
```

責務:

- `ui-events.js`: modal/message/page refresh等の共通HTMX UI event。
- `attendance-interactions.js`: 勤怠画面固有のinteractionとcalendar再取得。
- `calendar.js`: top calendarの日付選択とday detail取得。
- `analysis.js`: analysis画面固有のinteraction。
- `main.js`: theme/sidebar/HTMX共通設定等のapplication shell。

HTMX / Alpine.js等のvendor assetはasset buildで`assets/`へ配置する。application固有JSの置き場所としてvendor copyを`app/static/js`へ追加しない。generated assetは直接編集せず、既存build flowを利用する。

## Templates (`app/templates`)

```text
app/templates/
├── layout/
│   └── base.html
├── components/
│   ├── analysis/
│   ├── common/
│   ├── group/
│   ├── holiday/
│   ├── location/
│   ├── macros/
│   │   ├── attendance.html
│   │   ├── forms.html
│   │   ├── master_page.html
│   │   ├── modal.html
│   │   ├── navigation.html
│   │   └── ui.html
│   ├── partials/
│   │   ├── attendance/
│   │   ├── modals/
│   │   └── register/
│   ├── top/
│   ├── user/
│   └── user_type/
└── pages/
    ├── admin/
    │   └── database.html
    ├── auth/
    │   ├── admin_login.html
    │   ├── login.html
    │   └── settings.html
    ├── analysis.html
    ├── analysis_by_type.html
    ├── attendance.html
    ├── csv.html
    ├── group.html
    ├── holiday.html
    ├── location.html
    ├── register.html
    ├── top.html
    ├── user.html
    └── user_type.html
```

### `layout/`

application shell。shared head/sidebar/theme/script読込等を組み立てる。page固有のinteractionをここへ集約しない。

### `pages/`

browserへ返すfull-page template。認証画面は`pages/auth/`、SQLite DB管理は`pages/admin/database.html`へ分離する。

### `components/macros/`

複数templateで再利用するJinja macroを責務別に置く。

- `forms.html`: form error表示等
- `modal.html`: form/delete dialog shell
- `master_page.html`: master一覧のshared page element
- `navigation.html`: month/week navigation
- `attendance.html`: attendance modal/shared presentation
- `ui.html`: 既存template向けcompatibility facade

新規templateは必要な責務のmacroを直接importし、`ui.html`へ新しい共通機能を集約しない。

### `components/partials/`

HTMXで差し替える部分template。attendance calendar、modal、monthly registerのuser list/calendar等を置く。full pageと同じmarkupを別系統で複製しない。

### Domain components

`analysis/`, `group/`, `holiday/`, `location/`, `top/`, `user/`, `user_type/`等は各画面固有の表示componentを所有する。shared behaviorへ昇格する場合は既存macro/common責務との重複を確認する。

## Update rule

この文書はdirectory treeの完全なinventoryを目的にしない。新しいtop-level template責務や配置規則を追加・変更した場合だけ更新し、private partialの追加ごとに説明を重複させない。
