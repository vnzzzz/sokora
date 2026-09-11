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
| `/analysis` | monthly / fiscal-year trend and employee aggregation |
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
| Alpine.js | theme等の局所UI state |
| `sidebar.js` | sidebar open/closed toggleと`localStorage`永続化。stateは`html[data-sidebar-open]`、presentationはCSSが所有 |
| `ui-events.js` | modal / message / page refresh等の共通event |
| `attendance-interactions.js` | attendance/register画面固有interaction。対象pageだけでload |
| `calendar.js` | top calendarの日付選択 / detail取得。topだけでload |
| `analysis.js` | analysis画面のsticky shadow / HTMX failure fallback。期間・location更新はHTMX + server render |

sidebarの保存stateはCSS読込前にhead内の最小scriptで`html[data-sidebar-open]`へ反映し、初回paintから正しいshell geometryを使います。sidebar幅・main offset・label表示・navigation alignmentはCSSが所有し、Alpineのclass toggleには依存しません。

DB由来stateやHTMX lifecycleをAlpine global storeで共有状態として持ちません。
server-sideで決定できるnavigation active stateはJinjaでrenderし、page固有JSはglobal shellへ載せません。
HTML標準機能で十分な操作（CSV GET download等）はclient JSを追加せず実装します。

analysis画面は **表示条件 → 概要 → 社員別明細** の3層で情報を配置します。表示条件は他の分析結果と視覚的に区別した専用surfaceとし、月次/年度はform radioではなくanalysis viewのtab navigationとして扱います。active viewだけ対象月または対象年度のinputを表示し、同時に月次/年度の両datasetをreadしません。勤怠種別filterも同じ表示条件surfaceに置き、`details`で折りたためるようにして多数の選択肢が主可視化を押し下げ続けない構成にします。

概要には延べ登録日数・登録あり社員数とprimary time-series chartを置きます。trendは既存attendance analysis resultのlocation別date detailをpresentation serviceで日次/月次bucketへ変換し、Jinjaでsemantic SVGとしてrenderします。SVGにはaxis / grid / line / pointを持たせ、client-side chart stateや追加chart libraryは導入しません。月次は日別、年度は4月〜翌3月の月別trendです。その下に社員別明細tableを独立sectionとして置き、overviewとdetailを明確に分離します。

`#analysis-view` はmode / period変更のHTMX replacement boundaryで、browser historyへURLをpushします。集計対象は複数選択可能な勤怠種別filterで、同じpage adapterへGETし、`#analysis-table-region` だけをserver-sideで再renderします。このregionには選択件数、overview、SVG chart、社員別tableを含め、filter変更時にchartとdetailを同一read modelから同期更新します。選択状態はURL/historyへ残しません。history restore requestではfull pageを返し、HTMXは同じ `#analysis-view` history elementだけを復元します。通常のHTMX requestだけfragment responseにします。横長のSVG chartと集計tableはそれぞれ内部scroll surfaceを持ち、狭いviewportでpage全体を横overflowさせません。

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

local build、production image、Dev Containerはいずれも `scripts/build_assets.sh` を共通の
asset build boundaryとして利用します。Tailwind content scanやvendor bundle取得を各Dockerfileへ
重複実装しません。
