# UI requirements

Jinja2 + HTMX/Alpine.jsによるSSR UIの利用者向けbehaviorとpage adapter contractのSSoTとする。template/static fileの配置は [Template layout](templates.md)、API/DBのcontractは [API requirements](api.md) / [Database requirements](database.md) を参照する。SSR routeはapplication root配下に配置し、OpenAPIには含めない。

## Basic policy

- `layout/base.html`を共通layoutとし、full pageは`pages/`、reusable partial/macroは`components/`へ置く。
- HTMXでcalendar/modal/table等を部分更新する。serverが返す`HX-Trigger`はHTMX custom eventとして扱い、response headerの独自parseを複数箇所へ実装しない。
- JSON APIとHTMX write adapterはURL/transportを分離する。page/HTMX routeがForm input、HTML fragment、`HX-*` headerを担当し、business ruleは共通serviceを利用する。
- Alpine.jsはsidebar等の局所UI stateに限定し、DB由来stateやHTMX response lifecycleを共有storeとして所有しない。
- stylingはTailwind/daisyUI sourceから生成し、generated CSSを直接編集しない。

## Frontend responsibility boundary

- `static/js/ui-events.js`: modal/message/page refresh等の全画面共通HTMX UI event。
- `static/js/attendance-interactions.js`: 勤怠画面固有の月/週state、calendar再取得、勤怠modal interaction。
- `static/js/calendar.js`: top calendarの日付選択とday detail取得。
- `static/js/main.js`: theme、sidebar、HTMX共通設定等のapplication shell。
- 初回paint前に必要なtheme適用以外は、layout/headへpage interaction JavaScriptを埋め込まない。
- shared Jinja macroは責務別に`components/macros/`へ置く。`ui.html`は既存template向けcompatibility facadeで、新規templateから直接利用しない。

## Authentication / login

- `/auth/login`は、effective OIDC設定が有効な場合の「SSOでログイン」と、local admin loginへの明示的な入口を提供する。自動failoverは行わない。
- SSO buttonは`/auth/redirect`からOIDC Authorization Code flowを開始する。DBで明示disabled、設定不備、secret復号不能の場合はSSOを利用可能として表示しない。
- local admin loginは`/auth/login/admin`で行い、runtimeの`SOKORA_LOCAL_AUTH_ENABLED=true`かつadmin credentialが設定されている場合だけ利用できる。
- unauthenticated page accessは`/auth/login?next=...`へredirectする。nextはserver側でsame-origin pathへ制限する。
- `/auth/logout`は最初のresponseでapplication session identityを破棄する。OIDC sessionの場合だけ、その後の別request `/auth/logout/provider` でprovider logoutをbest-effort実行するため、shared DB / IdP停止がlocal logout完了をblockしない。
- `/auth/settings`はlocal admin専用のOIDC管理画面。
  - effective config source（`legacy_environment` / `database`）とOIDC/local admin状態を表示する。
  - issuer、client ID、scope、enable/disableを編集できる。
  - client secretはpassword inputから更新できるが、保存済み値をHTMLへ再表示しない。
  - Discovery接続確認は入力中issuerのstandard `/.well-known/openid-configuration`を検証し、保存を伴わない。OIDCを有効化して保存する場合も同じdiscovery検証を必須とし、metadataのissuer不一致や取得失敗ではDBへ有効設定を保存しない。
  - 「OIDC連携を解除」はDB rowを削除せずdisabled stateを残し、legacy environmentへのfallbackを防ぐ。
- DB rowがまだ存在しないupgrade直後だけlegacy `OIDC_*` environmentを利用する。最初にDB設定を保存/無効化した後はshared DBがOIDC stateのSSoTになる。

認証のsecurity/runtime contractは [API requirements](api.md) と [ADR 0002](adr/0002-authentication-runtime.md) を参照する。

## Calendar and attendance

- `/`: top page。`/calendar`からmonthly summaryをHTMX loadし、日付選択で`/calendar/day/{YYYY-MM-DD}`のdetailを取得する。
- `/calendar`: month queryに対応するsummary calendar。routerはHTTP input/renderを担当し、DB readとview model生成はcalendar read serviceへ委譲する。DB由来のprocess-local cacheは持たない。不正monthはcurrent monthへredirectし、DB/internal read failureを空calendarのHTTP 200へ変換しない。
- `/calendar/day/{day}`: daily attendance detail。request開始時点のDB stateからgroup/user type/location等をまとめて表示する。不正な日付pathはHTTP 400の明示的validation errorとし、「記録なし」のempty stateへ変換しない。
- `/attendance/weekly`: weekly attendance calendar。weekは1900–2100年の月曜日をsupported periodとし、範囲外・形式不正はcurrent weekへredirectする。routerはHTTP input/renderに集中し、user grouping・location master・period attendanceのread modelは`attendance_read_service`へ委譲する。user単位queryは行わない。cellからattendance modalを開き、writeは`/attendance/entries` page/HTMX adapterを利用する。
- `/attendance/monthly`: user list + user calendar。read modelは`attendance_read_service`へ集約し、user listは不要なcalendar queryを行わず、user calendarは対象user/periodだけを一括readする。`/attendance/monthly/users/{user_id}`、`/attendance/modals/{user_id}/{date}`等のHTMX partialを利用する。
- attendance write成功時は`closeModal` / `refreshAttendance` / `refreshUserAttendance`等の`HX-Trigger`を返し、clientが対象calendarを再取得する。
- refresh対象のmonth/weekは変更対象dateから導出し、`Referer`やtest専用headerをUI stateのSSoTにしない。
- application errorはHTML fragmentとしてmodal内へ返し、JSON API error responseをHTML targetへ流用しない。

## Master management

- `/users`、`/groups`、`/locations`、`/user-types`、`/holidays`は共通のmodal CRUD interaction contractを利用する。
- page/HTMX adapterがForm input、HTML fragment、`HX-*` headerを担当し、validation/transactionはserviceへ委譲する。JSON APIへ内部委譲しない。
- create/update/delete modalは`components/macros/modal.html`等のshared macroと`components/partials/modals/`を利用する。
- write成功時は`closeModal` / `refreshPage` / `showMessage`を返し、一覧はDBから再取得する。
- validation/application errorでは同一modalを再renderし、success triggerを返さない。
- relationship read、grouping、sorting等のview model生成はread serviceへ委譲し、routerでper-row queryを行わない。

## CSV and analysis

- `/csv`: month/encoding selection UI。downloadは`/api/v1/csv/download`を利用し、validationはAPI contractへ委譲する。
- `/analysis`: monthly/yearly aggregation view。routerはHTTP input/render、period/aggregation/sorting/view modelはanalysis serviceが担当する。年度指定は1900–2100をrequest validationで受け付け、不正な月次monthはcurrent monthへredirectする。DB/internal read failureを空のanalysis HTTP 200へ変換しない。

## Admin diagnostics and SQLite database management

- `/auth/settings`はlocal admin向けOIDC settings / diagnostics。shared DB設定の保存・無効化・unlink・discovery確認を提供する。
- `/admin/database`はadmin-only database management page。
- file-backed SQLiteではconsistent backup downloadと、明示確認付きrestoreを提供する。
- PostgreSQLおよびin-memory SQLiteではfile backup/restore操作を無効化し、利用できない理由を表示する。
- restore errorは管理画面へ表示するが、DB contentやsecretを露出しない。runtimeがfail-closedへfenceされた場合はservice restart/manual recoveryが必要になる。

SQLite backup/restoreのvalidation、maintenance、rollback contractは [SQLite database management](sqlite-database-management.md) を参照する。

## Cross references

- JSON API contract: [API requirements](api.md)
- data model / DB contract: [Database requirements](database.md)
- template/static layout: [Template layout](templates.md)
- documentation responsibility map: [Documentation guide](README.md)
