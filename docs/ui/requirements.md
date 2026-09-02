# UI 要件

Jinja2 + HTMX/Alpine.js による SSR UI の要件です。テンプレートの配置は [templates.md](./templates.md) を参照し、API/DB の前提はそれぞれの要件ドキュメントに委譲します。SSR ルートはアプリルート直下（`/attendance/...` など）に配置し、OpenAPI には含めません。

## 基本方針
- `layout/base.html` を共通レイアウトとして、ページテンプレートは `pages/*.html`、再利用部品は `components/` 配下に置く。
- HTMX を用いて部分更新（カレンダー/モーダル/テーブル差し替え）を行い、serverが返す `HX-Trigger` はHTMXが発火するcustom eventとして受ける。response headerを複数箇所で手動parseしない。
- JSON APIとHTMX write adapterはURL/transportを分離し、page/HTMX routeがForm入力・HTML fragment・`HX-*` headerを担当する。business ruleは共通serviceを呼ぶ。
- Alpine.js はsidebarなど局所的なUI stateに限定する。HTMX response lifecycleやDB由来stateの同期をAlpine storeへ持ち込まない。
- スタイルは DaisyUI/Tailwind 生成物を前提とし、生成 CSS 直接編集は避ける。

## フロントエンド責務境界
- `static/js/ui-events.js` は `openModal` / `closeModal` / `refreshPage` / `showMessage` など、全画面共通のHTMX UI eventだけを扱う。modal openは`HX-Trigger`がswap前に発火するため次tickへ遅延し、validation errorでdialogが置換された場合はopen状態を復元する。
- `static/js/attendance-interactions.js` は勤怠画面固有の月/週state、勤怠calendar再取得、ユーザーcalendar再取得、勤怠modal内の勤怠種別選択を扱う。`refreshUserAttendance` / `refreshAttendance` は1回の再取得へcoalesceする。
- `static/js/calendar.js` はトップ画面calendarの日付選択・day detail取得だけを扱う。勤怠月/週stateや画面遷移は所有しない。
- `static/js/main.js` はtheme、sidebar active state、HTMX共通設定などアプリshellに限定する。
- 初回paint前に必要なtheme適用以外は、layout/head内にinteraction JavaScriptを置かない。
- 共通Jinja macroは責務ごとに `components/macros/forms.html`、`modal.html`、`navigation.html`、`attendance.html`、`master_page.html` へ分ける。`components/macros/ui.html` は既存template向けの薄いcompatibility facadeであり、新規templateからは直接利用しない。

## 認証/ログインフロー
- ログインページ（`/auth/login`）で「Keycloak でログイン」と「管理者ローカルログイン」の2経路を並列表示する。自動フェイルオーバーは行わず、ユーザーが明示的に選択する。
- Keycloak ボタンは `/auth/redirect` に遷移し、エラーがあれば画面上部にメッセージを表示する。Keycloak 障害（HTTP 5xx/タイムアウト）時はメッセージのみ表示し、ローカル管理者経路を案内する。
- 管理者ローカルログインフォームは `SOKORA_LOCAL_ADMIN_USERNAME/PASSWORD` が設定されている場合のみ有効。認証失敗や設定不足は同ページにエラーを表示する。
- 認証状態が無い場合のページアクセスは `/auth/login?next=元URL` へリダイレクトし、「再ログインが必要です」旨を表示する。
- ログアウトは `/auth/logout` でアプリセッションを破棄し、OIDC 経路でログインしていて discovery metadata に `end_session_endpoint` がある場合は IdP のログアウトへ遷移した上で `/auth/login` に戻す。IdP logoutを利用できない場合もアプリセッションは破棄する。
- ローカル管理者専用の認証設定ページ（`/auth/settings`）はread-only diagnosticsとし、認証ガード・OIDC・ローカル管理者・session cookie設定の現在値/有効性を確認できる。OIDCのruntime toggleは持たず、有効性は共有runtime設定（`OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` / `OIDC_REDIRECT_URL`）から決定する。

## カレンダーと勤怠登録
- `/`（`pages/top.html`）：初期表示は空のコンテナ。`hx-get="/calendar"` で月次サマリーカレンダーを読み込み、クリックで `/calendar/day/{YYYY-MM-DD}` の勤怠詳細を表示する。
- `/calendar`（`routers/pages/calendar.py` → `components/top/summary_calendar.html`）：月指定 `?month=YYYY-MM` に対応。routerはHTTP入力とrenderのみを担当し、DB取得・月次view model生成・ロケーション色付けはcalendar read serviceへ委譲する。DB由来の月次表示にprocess-local cacheは持たず、各readで共有DBの最新状態から構築する。
- `/calendar/day/{day}`（`components/top/day_detail.html`）：日別read queryで勤怠・社員・グループ・社員種別・勤怠種別を一括取得し、calendar read serviceがグループ/社員種別単位へ編成する。モーダル経由の編集/削除後は `refreshAttendance`/`refreshUserAttendance` eventで対象calendarを再読込する。
- `/attendance/weekly`（`pages/attendance.html`）：週次カレンダーを SSR し、セルクリックで勤怠モーダルを開く。modalの作成/更新/削除は `/attendance/entries` page/HTMX adapterを呼び、成功時の `HX-Trigger`（`closeModal` `refreshAttendance` `refreshUserAttendance`）をclient event handlerが処理する。
- `/attendance/monthly`（`pages/register.html`）：ユーザー一覧（左）とユーザー別カレンダー（右）。ユーザー選択で `/attendance/monthly/users/{user_id}` を HTMX 取得し、勤怠modalは `/attendance/modals/{user_id}/{date}`、writeは `/attendance/entries` を利用する。`mode=register` クエリで月次UI用の文言を切り替える。
- 勤怠write後のrefresh対象月/週は変更対象の日付から導出する。`Referer`やテスト専用headerを表示状態のsourceとして使用しない。
- page/HTMX writeのapplication errorはHTML fragmentとしてmodal内のerror領域へretargetし、JSON API errorをHTML targetへ流用しない。

## マスタ管理 UI
- `/users`、`/groups`、`/locations`、`/user-types`、`/holidays` は同じ modal CRUD interaction contract を利用する。page/HTMX adapterがForm入力・HTML fragment・`HX-*` headerを担当し、validation/transactionは各application serviceへ委譲する。JSON APIへ内部委譲はしない。
- 一覧ページの追加ボタンは `/{master}/modal` を `hx-target="body"` / `hx-swap="beforeend"` で取得し、`openModal` eventでdialogを開く。編集は `/{master}/modal/{id}`、削除確認は `/{master}/delete-modal/{id}` を同じ方式で取得する。
- create/updateはmaster page routeへの `POST` / `PUT` を `components/macros/modal.html` の `modal_form` から送る。成功時は `closeModal`、`refreshPage`、`showMessage` を同じ `HX-Trigger` に返し、一覧は共有DBから再取得する。個別row mutation endpointやprocess-localなtable stateは持たない。
- validation/application errorはHTTP 200の同一modal fragmentとして返し、成功triggerは付けない。`ui-events.js` がouterHTML置換後のdialogを再度openし、入力エラーを同一modal内で表示する。
- deleteは `delete_modal_form` からpage routeへ `DELETE` し、成功時は空fragmentと `closeModal` / `refreshPage` / `showMessage` を返す。参照整合性等で削除できない場合は同じ削除確認modalへwarningを表示する。
- 社員一覧のrelationship取得・グループ編成/並び順、および勤怠種別のcategory編成はmaster read serviceがview modelを生成する。router内でper-row lookupや表示用groupingを行わない。
- master page間で共通するpage header/add action/empty stateは `components/macros/master_page.html`、dialog shell/form/delete interactionは `components/macros/modal.html`、form error表示は `components/macros/forms.html` を再利用する。各master固有templateは入力項目と表示列だけを所有する。

## CSV と分析
- `/csv`（`pages/csv.html`）：月選択とエンコーディング選択 UI。ダウンロードボタンが `/api/v1/csv/download` にクエリを付けてリダイレクトする。UI 側では単純なフォームで、バリデーションは API に委譲。
- `/analysis`（`pages/analysis.html`）：勤怠集計ビュー。routerは月/年度のHTTP入力とrenderのみを担当し、期間決定・集計・location category・group/user-type sorting・ユーザー行/date detailのview model生成はanalysis service/read serviceへ委譲する。月/年モード切替と勤怠種別の複数選択に対応し、選択した勤怠種別の件数・登録日付内訳を既存`analysis.js` interactionで更新する。

## 相互参照
- API 呼び出しの前提やレスポンス構造は [API 要件](../api/requirements.md) を参照。
- データモデルのカラムや制約は [DB 要件](../db/requirements.md) を参照。
- テンプレートの配置・命名規則は [templates.md](../templates.md) を参照し、UI 要件側では重複を避ける。
