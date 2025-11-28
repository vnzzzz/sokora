# UI 要件

Jinja2 + HTMX/Alpine.js による SSR UI の要件です。テンプレートの配置は [templates.md](./templates.md) を参照し、API/DB の前提はそれぞれの要件ドキュメントに委譲します。SSR ルートはアプリルート直下（`/attendance/...` など）に配置し、OpenAPI には含めません。旧プレフィックス `/ui` へのアクセスはリダイレクトで後方互換を保ちます。

## 基本方針
- `layout/base.html` を共通レイアウトとして、ページテンプレートは `pages/*.html`、再利用部品は `components/` 配下に置く。
- HTMX を用いて部分更新（カレンダー/モーダル/テーブル差し替え）を行い、`HX-Trigger` によるイベントでリロードを指示する。
- Alpine.js は軽量な UI 反応を補完する。スタイルは DaisyUI/Tailwind 生成物を前提とし、生成 CSS 直接編集は避ける。

## カレンダーと勤怠登録
- `/`（`pages/top.html`）：初期表示は空のコンテナ。`hx-get="/calendar"` で月次サマリーカレンダーを読み込み、クリックで `/calendar/day/{YYYY-MM-DD}` の勤怠詳細を表示する。
- `/calendar`（`routers/pages/calendar.py` → `components/top/summary_calendar.html`）：月指定 `?month=YYYY-MM` に対応。ロケーションごとの色クラスを付与し、前月/次月の HTMX ナビゲーションを提供。詳細パネルは `/calendar/day/{day}` を HTMX で差し替え。
- `/calendar/day/{day}`（`components/top/day_detail.html`）：勤怠種別ごと、またはグループごとにユーザーを並べる。モーダル経由の編集/削除後は `refreshAttendance`/`refreshUserAttendance` トリガーでカレンダーとユーザーカレンダーを再読込する。
- `/attendance/weekly`（`pages/attendance.html`）：週次カレンダーを SSR し、セルクリックで勤怠モーダルを開く。CRUD は `/api/v1/attendances` を呼び、成功時の `HX-Trigger`（`closeModal` `refreshAttendance`）を前提に UI を更新。
- `/attendance/monthly`（`pages/register.html`）：ユーザー一覧（左）とユーザー別カレンダー（右）。ユーザー選択で `/attendance/monthly/users/{user_id}` を HTMX 取得し、勤怠 CRUD のトリガーは `refreshUserAttendance` でモーダル後に再描画される。API は `/api/v1/attendances` を利用。モーダルは `/attendance/modals/{user_id}/{date}` を利用し、`mode=register` クエリで月次 UI 用の文言を切り替える。

## マスタ管理 UI
- `/users`（`pages/user.html`）：グループごとに社員一覧を表示。`/users/modal` を hx-get でロードし、作成/編集/削除は API `/api/v1/users` に委譲。モーダル閉鎖後は該当テーブルセクションのみを差し替える。
- `/locations`（`pages/location.html`）：カテゴリー単位のテーブル表示。`/locations/modal` から追加/編集モーダルを取得し、API `/api/v1/locations` と連動。削除もモーダル内の確認経由。
- `/groups`（`pages/group.html`）：グループ一覧テーブル。`/groups/modal` で追加/編集モーダルを取得し、CRUD は `/api/v1/groups` と整合させる。
- `/user-types`（`pages/user_type.html`）：社員種別一覧。`/user-types/modal` でモーダルを表示し、CRUD は `/api/v1/user_types` に委譲。
- これらのモーダルは `hx-target="body"` `hx-swap="beforeend"` で読み込み、共通の `components/macros/ui.html` / `components/common/modal.html` を利用する。テンプレートは `components/partials/modals/` に集約する。

## CSV と分析
- `/csv`（`pages/csv.html`）：月選択とエンコーディング選択 UI。ダウンロードボタンが `/api/v1/csv/download` にクエリを付けてリダイレクトする。UI 側では単純なフォームで、バリデーションは API に委譲。
- `/analysis`（`pages/analysis.html`）：勤怠集計ビュー。月/年モードの切替、グループ・勤怠種別の複数選択に対応し、テーブルは勤怠種別ごとの件数を表示する。表示順はロケーション `order` やグループ/社員種別の並び順を尊重する。詳細モードでは特定勤怠種別のユーザー別内訳を表示する。旧パス `/ui/analysis` は `/analysis` にリダイレクトされる。

## 相互参照
- API 呼び出しの前提やレスポンス構造は [API 要件](../api/requirements.md) を参照。
- データモデルのカラムや制約は [DB 要件](../db/requirements.md) を参照。
- テンプレートの配置・命名規則は [templates.md](../templates.md) を参照し、UI 要件側では重複を避ける。
