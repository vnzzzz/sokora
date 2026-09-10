# UI

browser UIはJinja2によるSSRを基本に、HTMXでpartial update、Alpine.jsで局所的なclient-side stateを扱います。page routeはOpenAPIへ含めません。

## Screens

| Route | Purpose |
| --- | --- |
| `/` | top / monthly calendar入口 |
| `/calendar` | monthly summary calendar |
| `/calendar/day/{day}` | 日別detail |
| `/attendance/weekly` | weekly attendance |
| `/attendance/monthly` | user別monthly attendance |
| `/users` | user master |
| `/groups` | group master |
| `/locations` | attendance/location master |
| `/user-types` | user type master |
| `/holidays` | custom holiday master |
| `/csv` | CSV download UI |
| `/analysis` | monthly / yearly aggregation |
| `/auth/*` | login / logout / OIDC protocol flow |
| `/admin/auth` | OIDC / authentication settings |
| `/admin/database` | SQLite backup / restore |

認証画面のbehaviorは [Authentication](authentication.md)、SQLite管理画面は [SQLite database management](sqlite-database-management.md) を参照してください。

## HTMX boundary

page / HTMX adapterがForm input、HTML fragment、`HX-*` headerを担当し、business ruleはserviceへ委譲します。

write成功時はcustom eventで必要なUIだけを更新します。代表例:

- `closeModal`
- `refreshPage`
- `refreshAttendance`
- `refreshUserAttendance`
- `showMessage`

validation / application errorは対象modalやfragmentへHTMLとして返し、success eventを送信しません。JSON API error responseをHTML targetへ流用しません。

refresh対象のmonth / weekは変更対象dateから導出し、`Referer`等から推測しません。

## Frontend responsibilities

| Technology / file | Responsibility |
| --- | --- |
| Jinja2 | full page / partial / reusable componentのrender |
| HTMX | server request、partial replacement、custom event |
| Alpine.js | sidebar / theme等の局所UI state |
| `ui-events.js` | modal / message / page refresh等の共通event |
| `attendance-interactions.js` | attendance/register画面固有interaction。対象pageだけでload |
| `calendar.js` | top calendarの日付選択 / detail取得。topだけでload |
| `analysis.js` | analysis画面固有interaction |

DB由来stateやHTMX lifecycleをAlpine global storeで共有状態として持ちません。
server-sideで決定できるnavigation active stateはJinjaでrenderし、page固有JSはglobal shellへ載せません。
HTML標準機能で十分な操作（CSV GET download等）はclient JSを追加せず実装します。

### Styling boundary

runtime dataからTailwind / daisyUI class名を組み立てません。

- Python/serviceは `text-primary` や `bg-success/15` のようなframework classを返さない
- Jinjaはruntime値をclass名へ埋め込まず、`data-*` attributeでsemantic stateを表現する
- actual color / background / visual mappingは `builder/input.css` が所有する
- Tailwind safelistをruntime presentation contractとして使わない
- Alpine等でclassをtoggleする場合も、sourceに完全なliteral classが存在する単純なUI stateに限定する

勤怠種別の色は永続 `location_id` を10個のpalette slotへ写像し、templateへは
`data-location-tone="0..9"` だけを渡します。名称変更や表示順変更ではtoneは変わりません。
実際の10色paletteはCSSだけで変更できます。

週末/祝日も `data-day-kind` で状態を渡し、色指定をtemplateから分離します。

## Template layout

```text
app/templates/
├── layout/       # application shell
├── pages/        # full-page templates
└── components/   # partials / macros / domain components
```

- `layout/base.html`: shared head / navigation / script loading
- `pages/`: browserへ返すfull page
- `components/partials/`: HTMX replacement unit
- `components/macros/`: reusable Jinja macro
- domain component directory: screen-specific presentation


`components/macros/ui.html`はlegacy template向けcompatibility facadeです。新規templateは必要な責務のmacroを直接importします。

## Assets

application JS sourceは`app/static/js/`、Tailwind/daisyUIとvendor JSのbuild sourceは`builder/`です。

generated assetを直接編集せず、次の既存flowを利用します。

```bash
make assets
```
