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
| `/analysis` | monthly / fiscal-year attendance coverage charts |
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
| `analysis.js` | analysis画面のHTMX failure fallbackとseriesの一括選択/解除。期間・selection更新はHTMX + server render |

sidebarの保存stateはCSS読込前にhead内の最小scriptで`html[data-sidebar-open]`へ反映し、初回paintから正しいshell geometryを使います。sidebar幅・main offset・label表示・navigation alignmentはCSSが所有し、Alpineのclass toggleには依存しません。

DB由来stateやHTMX lifecycleをAlpine global storeで共有状態として持ちません。
server-sideで決定できるnavigation active stateはJinjaでrenderし、page固有JSはglobal shellへ載せません。
HTML標準機能で十分な操作（CSV GET download等）はclient JSを追加せず実装します。

analysis画面は **表示条件 → 組織別グラフ → 社員種別別グラフ** の順で配置します。表示条件は他の分析結果と視覚的に区別した専用surfaceとし、月次/年度はform radioではなくanalysis viewのtab navigationとして扱います。active viewだけ対象月または対象年度のinputを表示し、同時に月次/年度の両datasetをreadしません。series selectionも同じ表示条件surfaceに置き、`details`で折りたためるようにして多数の選択肢が主可視化を押し下げ続けない構成にします。

初期表示は **全合計のみ** とし、個別勤務場所はすべて未選択です。全合計は個別勤務場所のselectionとは独立したsynthetic seriesで、そのbucketにいずれかの勤務場所を登録したunique社員数を全勤務場所横断で数えます。同一社員が同じ日/月に複数勤務場所を登録しても全合計では1人です。必要な勤務場所だけをcheckboxで追加して全合計と比較できます。selectionには「一括選択」「一括選択解除」を用意し、一括選択は全合計と全勤務場所をON、一括選択解除はすべてOFFにします。

主可視化は既存attendance analysis resultのlocation別date detailをserver-sideで再集約したline chartです。**組織ごと**、**社員種別ごと**にchartを分け、全合計および選択中の勤務場所をseriesとして描画します。月次は日別、年度は4月〜翌3月の月別で、個別勤務場所の縦軸値はそのbucketで該当勤務場所を登録したunique社員数です。同一社員が同じbucketで同じ勤務場所を複数回持っても1人として数えます。縦軸の0を常に表示し、系列が0へ落ちた日/月を「その区分で該当勤務者がいない」状態として直接読めることをprimary use caseにします。

1つのSVGへ重ねるseriesは最大10本とし、11本以上を同時表示する場合は同じ組織・社員種別内で追加panelへ10系列ずつ自動分割します。各panelは同じ縦軸scaleを共有し、凡例もpanel単位で表示します。これにより10色paletteや線種を循環させて同一SVG内の系列を見失うことを避けつつ、勤務場所数そのものには上限を設けません。

延べ登録日数、登録あり社員数等のKPI、coverage matrix、全体延べ登録日数trend、社員別集計tableはanalysisのprimary surfaceには置きません。限られた画面領域を勤務状況の時系列比較へ使います。chartはJinjaでserver-rendered SVGとしてrenderし、axis / grid / line / pointを持たせます。SVG自体に依存せず同じbucket / series / 人数を読み取れるvisually-hidden text summaryも併設します。client-side chart stateや追加chart libraryは導入しません。個別勤務場所の色は他画面と同じstable paletteを再利用し、同一panel内では線種も併用して色だけに依存しません。全合計は太いsolid lineとして個別seriesより強く表示します。

`#analysis-view` はmode / period変更のHTMX replacement boundaryで、browser historyへURLをpushします。series selectionは同じpage adapterへGETし、`#analysis-table-region` だけをserver-sideで再renderします。このregionには組織別・社員種別別chartを含め、selection変更時に両方を同一read snapshotから同期更新します。selection状態はURL/historyへ残しません。mode / period変更では初期の「全合計のみ」へ戻します。history restore requestではfull pageを返し、HTMXは同じ `#analysis-view` history elementだけを復元します。通常のHTMX requestだけfragment responseにします。横長chartは内部scroll surfaceを持ち、狭いviewportでpage全体を横overflowさせません。

### Styling boundary

runtime dataからTailwind / daisyUI class名を組み立てません。

- Python/serviceは `text-primary` や `bg-success/15` のようなframework classを返さない
- Jinjaはruntime値をclass名へ埋め込まず、`data-*` attributeでsemantic stateを表現する
- actual color / background / visual mappingは `builder/input.css` が所有する
- Tailwind safelistをruntime presentation contractとして使わない
- Alpine等でclassをtoggleする場合も、sourceに完全なliteral classが存在する単純なUI stateに限定する

勤務場所の色は永続 `location_id` を10個のpalette slotへ写像し、templateへは
`data-location-tone="0..9"` だけを渡します。名称変更や表示順変更ではtoneは変わりません。
実際の10色paletteはCSSだけで変更できます。analysis chartも同じ `get_location_tone()` の割当を再利用します。

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
