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
| `analysis.js` | analysis画面のHTMX failure fallback、勤怠種別の一括選択/解除、月次chartの日付から既存day detailを開くinteraction。期間・filter更新はHTMX + server render |

sidebarの保存stateはCSS読込前にhead内の最小scriptで`html[data-sidebar-open]`へ反映し、初回paintから正しいshell geometryを使います。sidebar幅・main offset・label表示・navigation alignmentはCSSが所有し、Alpineのclass toggleには依存しません。

DB由来stateやHTMX lifecycleをAlpine global storeで共有状態として持ちません。
server-sideで決定できるnavigation active stateはJinjaでrenderし、page固有JSはglobal shellへ載せません。
HTML標準機能で十分な操作（CSV GET download等）はclient JSを追加せず実装します。

analysis画面は **表示条件 → 人数推移chart → 月次の日別detail** の順で配置します。表示条件は、対象月/対象年度・グループ・社員種別を同じ行に並べ、その下に折りたたみ可能な勤怠種別controlを置きます。説明文を重ねず、label・selection state・chart自体で意味が伝わる構成にします。active viewだけ対象月または対象年度のinputを表示し、同時に月次/年度の両datasetをreadしません。

グループと社員種別は独立filterです。初期状態は **全グループ / 全社員種別** で、`グループA / 正社員` や `全グループ / 契約社員` のように交差条件で1つのchartを絞り込みます。複数のグループ別・社員種別別chartを縦に並べません。

勤怠種別は初期表示で **全合計のみ** とし、個別勤怠種別はすべて未選択です。全合計は個別勤怠種別のselectionとは独立したsynthetic seriesで、そのbucketにいずれかの勤怠種別を登録したunique社員数を全勤怠種別横断で数えます。同一社員が同じ日/月に複数勤怠種別を登録しても全合計では1人です。必要な勤怠種別だけをcheckboxで追加して全合計と比較できます。「全選択」「全解除」を用意します。

主可視化は既存attendance analysis resultのlocation別date detailをserver-sideで再集約した単一line chartです。月次は日別、年度は4月〜翌3月の月別で、個別勤怠種別の縦軸値はそのbucketで該当勤怠種別を登録したunique社員数です。同一社員が同じbucketで同じ勤怠種別を複数回持っても1人として数えます。縦軸の0を常に表示し、0人へ落ちた日/月を直接読めることをprimary use caseにします。

chartはlineだけで描画し、各bucketのpoint markerは表示しません。個別勤怠種別はstable 10-tone paletteと線種を併用し、全合計は太いsolid lineとして強く表示します。1つのSVGへ重ねるseriesは最大10本とし、11本以上を同時選択した場合は同じ対象filter内で追加panelへ10系列ずつ自動分割します。各panelは同じ縦軸scaleと凡例を共有し、10色paletteや線種の循環による同一SVG内での見分けづらさを避けます。SVGとは別に同じbucket / series / 人数を読み取れるvisually-hidden text summaryを併設します。

月次・年度とも日付/月ラベルはSVG内のx軸へ描画し、line bucketと同じx座標を共有します。月次の日付ラベルはinteractive controlでもあり、選択すると既存 `/calendar/day/{day}` の日別detailを同じanalysis pageのchart直下へHTMXで読み込みます。detailにはグループ・社員種別・社員名・勤怠種別を表示し、読み込み後はdetailが見える位置へscrollします。新しいdetail query/modelをanalysisへ重複実装しません。年度viewは月bucketのため日別detail controlを表示しません。

延べ登録日数、登録あり社員数等のKPI、coverage matrix、全体延べ登録日数trend、社員別集計tableはanalysisのprimary surfaceには置きません。chartはJinjaでserver-rendered SVGとしてrenderし、client-side chart stateや追加chart libraryは導入しません。

`#analysis-view` はmode / period変更のHTMX replacement boundaryで、browser historyへURLをpushします。グループ・社員種別・勤怠種別filterは同じpage adapterへGETし、`#analysis-table-region` だけをserver-sideで再renderします。filter状態はURL/historyへ残しません。mode / period変更では初期の「全グループ / 全社員種別・全合計のみ」へ戻します。history restore requestではfull pageを返し、HTMXは同じ `#analysis-view` history elementだけを復元します。通常のHTMX requestだけfragment responseにします。横長chartは内部scroll surfaceを持ち、狭いviewportでpage全体を横overflowさせません。

### Styling boundary

runtime dataからTailwind / daisyUI class名を組み立てません。

- Python/serviceは `text-primary` や `bg-success/15` のようなframework classを返さない
- Jinjaはruntime値をclass名へ埋め込まず、`data-*` attributeでsemantic stateを表現する
- actual color / background / visual mappingは `builder/input.css` が所有する
- Tailwind safelistをruntime presentation contractとして使わない
- Alpine等でclassをtoggleする場合も、sourceに完全なliteral classが存在する単純なUI stateに限定する

勤怠種別の色は永続 `location_id` を10個のpalette slotへ写像し、templateへは
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

`components/macros/` のmacroは責務別の `forms.html` / `navigation.html` / `attendance.html` を必要なtemplateから直接importします。compatibility facadeは置きません。

## Assets

application JS sourceは`app/static/js/`、Tailwind/daisyUIとvendor JSのbuild sourceは`builder/`です。

generated assetを直接編集せず、次の既存flowを利用します。

```bash
make assets
```

local build、production image、Dev Containerはいずれも `scripts/build_assets.sh` を共通の
asset build boundaryとして利用します。Tailwind content scanやvendor bundle取得を各Dockerfileへ
重複実装しません。
